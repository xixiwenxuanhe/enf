package main

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"io"
	"net/http"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/PuerkitoBio/goquery"
)

const MAX_CONCURRENCY = 1000 // 最大并发数，可根据需要修改

type Result struct {
	Link1   string
	Link2   string
	Email   string
	Website string
}

type CsvRow struct {
	Number  string
	Company string
	Link1   string
}

// 增强邮箱提取，支持明文、mailto、let eee三种
func extractEmailFromScript(html string) string {
	// 1. 先找 let eee = 'xxx' 形式
	reEEE := regexp.MustCompile(`let\s+eee\s*=\s*['\"]([^'\"]+)['\"]`)
	matchEEE := reEEE.FindStringSubmatch(html)
	if len(matchEEE) > 1 {
		encoded := matchEEE[1]
		email := strings.Replace(encoded, "#109#103#.cn", "@", 1)
		email = strings.Replace(email, "#103#example123cn", ".com", 1)
		if strings.Contains(email, "@") {
			return email
		}
	}
	// 2. 再找 mailto:xxx@xxx
	reMailto := regexp.MustCompile(`mailto:([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)`)
	matchMailto := reMailto.FindStringSubmatch(html)
	if len(matchMailto) > 1 {
		return matchMailto[1]
	}
	// 3. 再找明文邮箱
	rePlain := regexp.MustCompile(`[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+`)
	matchPlain := rePlain.FindStringSubmatch(html)
	if len(matchPlain) > 0 {
		return matchPlain[0]
	}
	return ""
}

func fetchDetail(link1 string, client *http.Client) (string, string) {
	url := link1
	if !strings.HasPrefix(link1, "http") {
		url = "https://www.enf.com.cn" + link1
	}
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36")
	resp, err := client.Do(req)
	if err != nil {
		return "", ""
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	html := string(body)
	doc, _ := goquery.NewDocumentFromReader(strings.NewReader(html))
	link2, _ := doc.Find(`a[itemprop=\"url\"]`).Attr("href")
	email := extractEmailFromScript(html)
	return link2, email
}

func main() {
	// 用户直接指定要处理的文件
	files := []string{
		"procedure1/seller_India_Email20250508.csv",
		// "procedure1/seller_United%20States_Email20250508.csv",
	}
	for _, filename := range files {
		fmt.Printf("处理文件: %s\n", filename)
		f, err := os.Open(filename)
		if err != nil {
			fmt.Printf("无法打开文件 %s: %v\n", filename, err)
			continue
		}
		reader := csv.NewReader(bufio.NewReader(f))
		head, err := reader.Read()
		if err != nil {
			fmt.Printf("读取头部失败: %v\n", err)
			f.Close()
			continue
		}
		idxNumber, idxCompany, idxEmail, idxWebsite := -1, -1, -1, -1
		for i, h := range head {
			switch strings.TrimSpace(h) {
			case "Number":
				idxNumber = i
			case "Company Name":
				idxCompany = i
			case "Email":
				idxEmail = i
			case "Website":
				idxWebsite = i
			}
		}
		if idxNumber == -1 || idxCompany == -1 || idxEmail == -1 || idxWebsite == -1 {
			fmt.Printf("文件 %s 缺少必要字段\n", filename)
			f.Close()
			continue
		}
		var records [][]string
		var needFetchIdx []int
		var needFetchLinks []string
		for idx := 0; ; idx++ {
			record, err := reader.Read()
			if err != nil {
				break
			}
			records = append(records, record)
			if strings.TrimSpace(record[idxEmail]) == "" {
				needFetchIdx = append(needFetchIdx, idx)
				needFetchLinks = append(needFetchLinks, record[idxWebsite])
			}
		}
		f.Close()

		// 并发抓取邮箱
		type fetchResult struct {
			Idx   int
			Email string
		}
		results := make([]fetchResult, len(needFetchIdx))
		wg := sync.WaitGroup{}
		sem := make(chan struct{}, MAX_CONCURRENCY) // 用户可指定
		for i, idx := range needFetchIdx {
			wg.Add(1)
			go func(i, idx int, link1 string) {
				defer wg.Done()
				sem <- struct{}{}
				client := &http.Client{Timeout: 10 * time.Second}
				_, email := fetchDetail(link1, client)
				warn := ""
				if email == "alan@enfsolar.com" {
					email = ""
					warn = " [警告: 并发限制邮箱]"
				}
				results[i] = fetchResult{Idx: idx, Email: email}
				fmt.Printf("%s %s 填充邮箱: %s%s\n", records[idx][idxNumber], records[idx][idxCompany], email, warn)
				<-sem
			}(i, idx, needFetchLinks[i])
		}
		wg.Wait()

		// 写回邮箱
		for _, r := range results {
			records[r.Idx][idxEmail] = r.Email
		}

		// 统计填充情况
		successCount := 0
		for _, r := range results {
			if r.Email != "" {
				successCount++
			}
		}
		remainCount := 0
		totalCount := len(records)
		for _, rec := range records {
			if strings.TrimSpace(rec[idxEmail]) == "" {
				remainCount++
			}
		}
		remainPercent := 0.0
		if totalCount > 0 {
			remainPercent = float64(remainCount) * 100.0 / float64(totalCount)
		}

		// 重新写回原文件
		out, err := os.Create(filename)
		if err != nil {
			fmt.Printf("无法写入文件 %s: %v\n", filename, err)
			continue
		}
		writer := csv.NewWriter(out)
		writer.Write(head)
		for _, r := range records {
			writer.Write(r)
		}
		writer.Flush()
		out.Close()
		fmt.Printf("文件 %s 处理完成\n", filename)
		fmt.Printf("本次成功填充了%d个，还剩%d个（%.2f%%）\n", successCount, remainCount, remainPercent)
	}
	fmt.Println("全部文件处理完成！")
}

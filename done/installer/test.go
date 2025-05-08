package main

import (
	"compress/gzip"
	"crypto/tls"
	"encoding/csv"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
	"github.com/PuerkitoBio/goquery"
	"github.com/andybalholm/brotli"
	"errors"
)

type Company struct {
	Number  string
	Name    string
	Address string
	Link1   string
	Link2   string
	Email   string
}

var httpClient = &http.Client{
	Timeout: 5 * time.Second, // 本地网络最多5秒
	Transport: &http.Transport{
		DialContext: (&net.Dialer{
			Timeout:   2 * time.Second,  // 连接超时
			KeepAlive: 30 * time.Second, // 保持连接
		}).DialContext,
		TLSHandshakeTimeout:   2 * time.Second,
		ResponseHeaderTimeout: 3 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,
		MaxIdleConns:          10,
		IdleConnTimeout:       30 * time.Second,
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
	},
}

// 超时读取器，用于处理读取超时
type timeoutReader struct {
	r       io.Reader
	timeout time.Duration
}

func (tr *timeoutReader) Read(p []byte) (n int, err error) {
	ch := make(chan readResult, 1)
	
	go func() {
		n, err := tr.r.Read(p)
		ch <- readResult{n, err}
	}()
	
	select {
	case res := <-ch:
		return res.n, res.err
	case <-time.After(tr.timeout):
		return 0, errors.New("读取超时")
	}
}

type readResult struct {
	n   int
	err error
}

func extractEmail(text string) string {
	// 支持 @、[at]、(at) 三种写法，允许中间有空格
	patterns := []string{
		`[\w\.-]+\s*@\s*[\w\.-]+\.[a-zA-Z]{2,}`,
		`[\w\.-]+\s*\[at\]\s*[\w\.-]+\.[a-zA-Z]{2,}`,
		`[\w\.-]+\s*\(at\)\s*[\w\.-]+\.[a-zA-Z]{2,}`,
	}
	for _, pat := range patterns {
		re := regexp.MustCompile("(?i)" + pat)
		match := re.FindString(text)
		if match != "" {
			// 标准化邮箱
			match = strings.ReplaceAll(match, "(at)", "@")
			match = strings.ReplaceAll(match, "[at]", "@")
			match = strings.ReplaceAll(match, " ", "")
			return match
		}
	}
	return ""
}

func processFile(inputFile string, maxConcurrency int) {
	start := time.Now()

	file, err := os.Open(inputFile)
	if err != nil {
		log.Printf("无法打开CSV文件 %s：%v\n", inputFile, err)
		return
	}
	defer file.Close()
	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		log.Printf("读取CSV失败 %s：%v\n", inputFile, err)
		return
	}

	var companies []Company
	for i, row := range records {
		if i == 0 {
			continue // 跳过表头
		}
		if len(row) < 5 {
			continue
		}
		companies = append(companies, Company{
			Number:  row[0],
			Name:    row[1],
			Address: row[2],
			Link1:   row[3],
			Link2:   row[4],
			Email:   "",
		})
	}
	
	fmt.Printf("读取到 %d 条记录\n", len(companies))

	// 创建临时文件用于存储处理结果
	baseName := inputFile
	if idx := strings.LastIndex(inputFile, "/"); idx != -1 {
		baseName = inputFile[idx+1:]
	}
	tempFile := "procedure1/temp_" + strings.Replace(baseName, "Company", "Procedure1", 1)
	outputFile := "procedure1/" + strings.Replace(baseName, "Company", "Procedure1", 1)
	
	// 确保目录存在
	os.MkdirAll("procedure1", 0755)
	
	tempOut, err := os.Create(tempFile)
	if err != nil {
		log.Printf("无法创建临时CSV：%v\n", err)
		return
	}
	defer tempOut.Close()
	tempWriter := csv.NewWriter(tempOut)
	defer tempWriter.Flush()
	
	// 写入表头
	tempWriter.Write([]string{"Number", "Company Name", "Company Website", "Email"})

	var wg sync.WaitGroup
	var mu sync.Mutex // 保护文件写入
	sem := make(chan struct{}, maxConcurrency) // 控制最大并发
	
	for i := range companies {
		wg.Add(1)
		sem <- struct{}{} // 占用一个名额
		go func(i int) {
			defer wg.Done()
			defer func() { <-sem }() // 释放名额

			link := companies[i].Link2
			company := companies[i] // 拷贝，避免并发问题
			if link == "" {
				company.Email = ""
				mu.Lock()
				tempWriter.Write([]string{company.Number, company.Name, company.Link2, ""})
				tempWriter.Flush() // 确保立即写入
				mu.Unlock()
				fmt.Printf("%s,%s,%s,%s,,E1001,\n", company.Number, company.Name, company.Address, link)
				return
			}

			// 标准请求
			req, err := http.NewRequest("GET", link, nil)
			if err != nil {
				company.Email = ""
				mu.Lock()
				tempWriter.Write([]string{company.Number, company.Name, company.Link2, ""})
				tempWriter.Flush()
				mu.Unlock()
				fmt.Printf("%s,%s,%s,%s,,请求失败: %v\n", company.Number, company.Name, company.Address, link, err)
				return
			}
			
			req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
			req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
			req.Header.Set("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
			req.Header.Set("Accept-Encoding", "gzip, deflate, br")
			req.Header.Set("Connection", "keep-alive")
			req.Header.Set("Referer", "https://www.google.com/")
			req.Header.Set("Upgrade-Insecure-Requests", "1")
			req.Header.Set("Cache-Control", "max-age=0")
			req.Header.Set("Pragma", "no-cache")
			
			resp, err := httpClient.Do(req)
			if err != nil || resp == nil || resp.StatusCode != 200 {
				if resp != nil {
					resp.Body.Close()
				}
				company.Email = ""
				mu.Lock()
				tempWriter.Write([]string{company.Number, company.Name, company.Link2, ""})
				tempWriter.Flush()
				mu.Unlock()
				fmt.Printf("%s,%s,%s,%s,,请求失败\n", company.Number, company.Name, company.Address, link)
				return
			}
			defer resp.Body.Close()
			// 处理可能的压缩响应
			var reader io.Reader
			encoding := resp.Header.Get("Content-Encoding")
			switch encoding {
			case "gzip":
				timeoutReader := &timeoutReader{r: resp.Body, timeout: 3 * time.Second}
				gzr, err := gzip.NewReader(timeoutReader)
				if err != nil {
					company.Email = ""
					mu.Lock()
					tempWriter.Write([]string{company.Number, company.Name, company.Link2, ""})
					tempWriter.Flush()
					mu.Unlock()
					fmt.Printf("%s,%s,%s,%s,,解压gzip失败: %v\n", company.Number, company.Name, company.Address, link, err)
					return
				}
				defer gzr.Close()
				reader = gzr
			case "br":
				timeoutReader := &timeoutReader{r: resp.Body, timeout: 3 * time.Second}
				reader = brotli.NewReader(timeoutReader)
			default:
				reader = resp.Body
			}
			doc, err := goquery.NewDocumentFromReader(reader)
			if err != nil {
				company.Email = ""
				mu.Lock()
				tempWriter.Write([]string{company.Number, company.Name, company.Link2, ""})
				tempWriter.Flush()
				mu.Unlock()
				fmt.Printf("%s,%s,%s,%s,,解析失败: %v\n", company.Number, company.Name, company.Address, link, err)
				return
			}
			email := extractEmail(doc.Text())
			company.Email = email
			
			// 清理邮箱格式
			email = strings.ReplaceAll(email, "\n", "")
			email = strings.ReplaceAll(email, "\r", "")
			email = strings.TrimSpace(email)
			
			mu.Lock()
			tempWriter.Write([]string{company.Number, company.Name, company.Link2, email})
			tempWriter.Flush()
			mu.Unlock()
			
			if email != "" {
				fmt.Printf("%s,%s,%s,%s,%s,成功\n", company.Number, company.Name, company.Address, link, email)
			} else {
				if resp.StatusCode == 200 {
					fmt.Printf("%s,%s,%s,%s,,网站源代码并没有邮件信息，需要进一步处理...\n", company.Number, company.Name, company.Address, link)
				} else {
					fmt.Printf("%s,%s,%s,%s,,状态码: %d\n", company.Number, company.Name, company.Address, link, resp.StatusCode)
				}
			}
		}(i)
	}
	wg.Wait()
	tempWriter.Flush()
	tempOut.Close()

	// 读取临时文件，排序后写入最终文件
	tempData, err := os.Open(tempFile)
	if err != nil {
		log.Printf("无法打开临时文件：%v\n", err)
		return
	}
	defer tempData.Close()
	
	csvReader := csv.NewReader(tempData)
	records, err = csvReader.ReadAll()
	if err != nil {
		log.Printf("读取临时CSV失败：%v\n", err)
		return
	}
	
	// 跳过表头进行排序
	header := records[0]
	dataRecords := records[1:]
	
	// 按Number排序
	sort.Slice(dataRecords, func(i, j int) bool {
		numI, errI := strconv.Atoi(dataRecords[i][0])
		numJ, errJ := strconv.Atoi(dataRecords[j][0])
		if errI == nil && errJ == nil {
			return numI < numJ
		}
		return dataRecords[i][0] < dataRecords[j][0]
	})
	
	// 写入最终排序后的文件
	outfile, err := os.Create(outputFile)
	if err != nil {
		log.Printf("无法创建输出CSV：%v\n", err)
		return
	}
	defer outfile.Close()
	writer := csv.NewWriter(outfile)
	defer writer.Flush()
	
	// 写入表头
	writer.Write(header)
	
	// 写入排序后的数据
	for _, record := range dataRecords {
		writer.Write(record)
	}
	writer.Flush()
	
	// 删除临时文件
	os.Remove(tempFile)

	fmt.Printf("邮箱提取完成，结果已保存到 %s\n", outputFile)
	fmt.Printf("总耗时：%v\n", time.Since(start))

	// 统计输出
	totalCount := len(dataRecords)
	failCount := 0
	for _, record := range dataRecords {
		if len(record) > 3 && record[3] == "" {
			failCount++
		}
	}
	failRate := 0.0
	if totalCount > 0 {
		failRate = float64(failCount) / float64(totalCount) * 100
	}
	fmt.Printf("总记录数：%d，失败数：%d，失败率：%.2f%%\n", totalCount, failCount, failRate)
}

func main() {
	maxConcurrency := flag.Int("maxConcurrency", 100, "最大并发数")
	flag.Parse()

	inputFiles := []string{
		"Company/installer_Australia_Company20250508.csv",
		"Company/installer_Austria_Company20250509.csv",
		"Company/installer_Belgium_Company20250509.csv",
		"Company/installer_Brazil_Company20250509.csv",
		"Company/installer_Canada_Company20250509.csv",
		"Company/installer_Czech%20Republic_Company20250509.csv",
		"Company/installer_France_Company20250508.csv",
		"Company/installer_Germany_Company20250507.csv",
		"Company/installer_India_Company20250509.csv",
		"Company/installer_Italy_Company20250508.csv",
		"Company/installer_Netherlands_Company20250508.csv",
		"Company/installer_Poland_Company20250508.csv",
		"Company/installer_Spain_Company20250507.csv",
		"Company/installer_Switzerland_Company20250509.csv",
		"Company/installer_United%20Kingdom_Company20250508.csv",
		"Company/installer_United%20States_Company20250509.csv",
	}

	for _, inputFile := range inputFiles {
		fmt.Printf("\n==== 开始处理文件：%s ===="+"\n", inputFile)
		processFile(inputFile, *maxConcurrency)
	}
}

package main

import (
	"fmt"
	"io"
	"net/http"
	"regexp"
	"strings"
	"time"
	"compress/gzip"

	// brotli解码库
	"github.com/andybalholm/brotli"
)

func main() {
	url := "https://www.solar-zimmerei.de"
	fmt.Printf("开始测试访问 %s\n", url)

	client := &http.Client{
		Timeout: 15 * time.Second,
	}

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		fmt.Printf("请求创建失败: %v\n", err)
		return
	}
	// 尽量模拟真实浏览器
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
	req.Header.Set("Accept-Encoding", "gzip, deflate, br")
	req.Header.Set("Connection", "keep-alive")
	req.Header.Set("Referer", "https://www.google.com/")
	req.Header.Set("Upgrade-Insecure-Requests", "1")
	req.Header.Set("Cache-Control", "max-age=0")
	req.Header.Set("Pragma", "no-cache")
	// 如有需要可加Cookie
	// req.Header.Set("Cookie", "从浏览器复制的cookie内容")

	resp, err := client.Do(req)
	if err != nil {
		fmt.Printf("请求失败: %v\n", err)
		return
	}
	defer resp.Body.Close()

	fmt.Printf("响应状态码: %d\n", resp.StatusCode)
	if resp.StatusCode == 403 {
		fmt.Println("状态码: 403 —— 服务器禁止访问（Forbidden）")
	} else {
		fmt.Printf("实际状态码: %d\n", resp.StatusCode)
		if resp.StatusCode == 200 {
			// 自动解压响应内容
			var reader io.Reader
			encoding := resp.Header.Get("Content-Encoding")
			switch encoding {
			case "gzip":
				gzr, err := gzip.NewReader(resp.Body)
				if err != nil {
					fmt.Printf("解压gzip失败: %v\n", err)
					return
				}
				defer gzr.Close()
				reader = gzr
			case "br":
				reader = brotli.NewReader(resp.Body)
			default:
				reader = resp.Body
			}
			body, err := io.ReadAll(reader)
			if err != nil {
				fmt.Printf("读取页面内容失败: %v\n", err)
				return
			}
			contentStr := string(body)
			email := extractEmail(contentStr)
			if email != "" {
				fmt.Printf("提取到邮箱: %s\n", email)
			} else {
				fmt.Println("页面中未提取到邮箱")
				fmt.Println("\n页面完整内容如下:\n====================\n")
				fmt.Println(contentStr)
				fmt.Println("\n====================\n")
			}
		}
	}
}

// 支持 @、[at]、(at) 三种写法，允许中间有空格
func extractEmail(text string) string {
	patterns := []string{
		`[\w\.-]+\s*@\s*[\w\.-]+\.[a-zA-Z]{2,}`,
		`[\w\.-]+\s*\[at\]\s*[\w\.-]+\.[a-zA-Z]{2,}`,
		`[\w\.-]+\s*\(at\)\s*[\w\.-]+\.[a-zA-Z]{2,}`,
	}
	for _, pat := range patterns {
		re := regexp.MustCompile("(?i)" + pat)
		match := re.FindString(text)
		if match != "" {
			match = strings.ReplaceAll(match, "(at)", "@")
			match = strings.ReplaceAll(match, "[at]", "@")
			match = strings.ReplaceAll(match, " ", "")
			return match
		}
	}
	return ""
}


// wenxuan@dev enf$ go run test/resolve403.go 
// 开始测试访问 https://www.solar-zimmerei.de
// 响应状态码: 200
// 实际状态码: 200
// 提取到邮箱: info@solar-zimmerei.de

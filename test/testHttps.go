package main

import (
	"fmt"
	"io"
	"net/http"
	"crypto/tls"
	"regexp"
	"strings"
	"time"
)

func main() {
	// 直接使用HTTP协议访问X-ELIO网站
	url := "https://www.x-elio.com"
	fmt.Printf("开始测试直接访问 %s\n", url)

	// 创建请求
	client := &http.Client{
		Timeout: 15 * time.Second,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			return http.ErrUseLastResponse
		},
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
		},
	}
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		fmt.Printf("创建请求失败: %v\n", err)
		return
	}

	// 设置请求头模拟浏览器
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")

	// 发送请求
	resp, err := client.Do(req)
	if err != nil {
		fmt.Printf("请求失败: %v\n", err)
		return
	}
	defer resp.Body.Close()

	// 输出响应状态
	fmt.Printf("响应状态: %s\n", resp.Status)
	fmt.Printf("响应头:\n")
	for k, v := range resp.Header {
		fmt.Printf("  %s: %s\n", k, v)
	}

	// 读取并输出网页内容
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Printf("读取响应失败: %v\n", err)
		return
	}

	contentStr := string(body)
	// 输出网页完整内容
	fmt.Printf("\n网页完整内容:\n%s\n", contentStr)

	// 检查是否有可能的重定向到HTTPS
	if strings.Contains(contentStr, "https://www.x-elio.com") {
		fmt.Println("\n⚠️ 注意：页面中包含HTTPS URL，可能在JavaScript中进行了重定向")
	}

	// 使用 extractEmail 提取邮箱
	email := extractEmail(contentStr)
	if email != "" {
		fmt.Printf("\n提取到邮箱: %s\n", email)
	} else {
		fmt.Println("\n未提取到邮箱")
	}
	
	fmt.Println("\n测试完成")
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

// 支持 @、[at]、(at) 三种写法，允许中间有空格
func extractEmail(text string) string {
	patterns := []string{
		`[w\.-]+\s*@\s*[\w\.-]+\.[a-zA-Z]{2,}`,
		`[w\.-]+\s*\[at\]\s*[\w\.-]+\.[a-zA-Z]{2,}`,
		`[w\.-]+\s*\(at\)\s*[\w\.-]+\.[a-zA-Z]{2,}`,
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
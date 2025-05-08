package main

import (
	"crypto/tls"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"time"
	"compress/gzip"
	"context"

	// brotli解码库
	"github.com/andybalholm/brotli"
	"golang.org/x/net/proxy"
)

// 代理账号信息
var proxyAccounts = []struct {
	Username string
	Password string
}{
	{"yangyangmao-rotate", "yangyangmao"},
	{"iu7zso75luk-rotate", "iu7zso75luk"},
	{"shengshi-rotate", "shengshi"},
	{"xixiwenxuanhe-rotate", "xixiwenxuanhe"},
}

func main() {
	url := "https://www.holzbau-gessler.de"
	fmt.Printf("开始测试访问 %s\n", url)

	// 直接使用代理方法
	fmt.Println("\n使用SOCKS5代理进行访问")
	err := tryWithProxy(url)
	if err == nil {
		fmt.Printf("\n成功通过代理访问网站！\n")
	} else {
		fmt.Printf("代理访问失败: %v\n", err)
	}
}

// 使用SOCKS5代理
func tryWithProxy(targetURL string) error {
	fmt.Println("尝试使用SOCKS5代理...")
	
	// 尝试所有代理
	for i, account := range proxyAccounts {
		proxyURL := fmt.Sprintf("socks5://%s:%s@p.webshare.io:80", account.Username, account.Password)
		fmt.Printf("  尝试代理 %d: %s\n", i+1, proxyURL)
		
		// 创建一个自定义的拨号器
		dialer, err := createProxyDialer(proxyURL)
		if err != nil {
			fmt.Printf("  代理 %d 配置失败: %v\n", i+1, err)
			continue
		}
		
		transport := &http.Transport{
			DialContext: func(ctx context.Context, network, addr string) (net.Conn, error) {
				return dialer.Dial(network, addr)
			},
			TLSClientConfig: &tls.Config{
				InsecureSkipVerify: true,
			},
		}
		
		client := &http.Client{
			Transport: transport,
			Timeout:   30 * time.Second,
		}
		
		req, err := http.NewRequest("GET", targetURL, nil)
		if err != nil {
			fmt.Printf("  代理 %d 创建请求失败: %v\n", i+1, err)
			continue
		}
		
		// 添加完整的请求头
		req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
		req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
		req.Header.Set("Accept-Language", "de-DE,de;q=0.9,en;q=0.8") // 使用德语首选
		req.Header.Set("Accept-Encoding", "gzip, deflate, br")
		req.Header.Set("Connection", "keep-alive")
		req.Header.Set("Referer", "https://www.google.com/")
		req.Header.Set("Upgrade-Insecure-Requests", "1")
		req.Header.Set("Cache-Control", "max-age=0")
		
		fmt.Printf("  使用代理 %d 发送请求...\n", i+1)
		resp, err := client.Do(req)
		if err != nil {
			fmt.Printf("  代理 %d 请求失败: %v\n", i+1, err)
			continue
		}
		
		fmt.Printf("  代理 %d 连接成功! 状态码: %d\n", i+1, resp.StatusCode)
		defer resp.Body.Close()
		return processResponse(resp)
	}
	
	return fmt.Errorf("所有代理均请求失败")
}

// 创建代理拨号器
func createProxyDialer(proxyURL string) (proxy.Dialer, error) {
	// 解析代理URL
	parsedURL, err := url.Parse(proxyURL)
	if err != nil {
		return nil, fmt.Errorf("解析代理URL失败: %v", err)
	}
	
	// 创建SOCKS5代理拨号器
	auth := &proxy.Auth{}
	if parsedURL.User != nil {
		auth.User = parsedURL.User.Username()
		if password, ok := parsedURL.User.Password(); ok {
			auth.Password = password
		}
	}
	
	// 连接代理服务器
	dialer, err := proxy.SOCKS5("tcp", parsedURL.Host, auth, proxy.Direct)
	if err != nil {
		return nil, fmt.Errorf("创建SOCKS5代理拨号器失败: %v", err)
	}
	
	return dialer, nil
}

// 处理响应
func processResponse(resp *http.Response) error {
	fmt.Printf("状态码: %d\n", resp.StatusCode)
	
	// 自动处理各种编码
	var reader io.Reader
	encoding := resp.Header.Get("Content-Encoding")
	switch encoding {
	case "gzip":
		gzr, err := gzip.NewReader(resp.Body)
		if err != nil {
			return fmt.Errorf("解压gzip失败: %v", err)
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
		return fmt.Errorf("读取页面内容失败: %v", err)
	}
	
	contentStr := string(body)
	
	// 提取网页标题，帮助判断连接是否成功
	titleRe := regexp.MustCompile(`<title[^>]*>(.*?)</title>`)
	titleMatch := titleRe.FindStringSubmatch(contentStr)
	if len(titleMatch) > 1 {
		fmt.Printf("网页标题: %s\n", titleMatch[1])
	}
	
	// 提取邮箱
	email := extractEmail(contentStr)
	if email != "" {
		fmt.Printf("提取到邮箱: %s\n", email)
	} else {
		fmt.Println("页面中未提取到邮箱")
		// 仅在调试模式下输出页面内容
		//fmt.Println("\n页面完整内容如下:\n====================\n")
		//fmt.Println(contentStr)
		//fmt.Println("\n====================\n")
	}
	
	return nil
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

// wenxuan@dev enf$ go run test/test403.go 
// 开始测试访问 https://www.solar-zimmerei.de
// 响应状态码: 200
// 实际状态码: 200
// 提取到邮箱: info@solar-zimmerei.de
const puppeteer = require('puppeteer');
const { extractFromHtml } = require('./content');

async function extract(url) {
    console.log(`使用 Puppeteer 抓取 URL: ${url}`);
    let browser = null;
    try {
        browser = await puppeteer.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        const page = await browser.newPage();
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');
        await page.goto(url, { waitUntil: 'networkidle0', timeout: 180000 });

        const html = await page.content();
        console.log('成功获取页面内容 (Puppeteer)，准备解析...');
        return extractFromHtml(html);
    } catch (error) {
        console.error(`Puppeteer 抓取或解析URL失败 (${url}): ${error.message}`);
        if (error.name === 'TimeoutError') {
            console.error('Puppeteer 导航超时，页面可能过于复杂或网络问题。');
        }
        throw error;
    } finally {
        if (browser) {
            await browser.close();
            console.log('Puppeteer 浏览器已关闭');
        }
    }
}

module.exports = extract;

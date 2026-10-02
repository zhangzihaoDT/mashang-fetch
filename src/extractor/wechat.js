const cheerio = require('cheerio');
const http = require('../http');
const { cleanText, extractTables } = require('./content');

async function extract(url) {
    console.log(`使用 Axios 抓取微信文章 URL: ${url}`);
    const response = await http.get(url);
    console.log(`成功获取页面内容 (Axios)，状态码: ${response.status}`);

    const $ = cheerio.load(response.data);
    $('script').remove();
    $('style').remove();

    const title = $('#activity-name').text().trim();
    const author = $('#js_name').text().trim();

    let body = '';
    const contentElement = $('#js_content');
    if (contentElement.length > 0) {
        body = cleanText(contentElement.text());
    }
    if (!body) {
        body = cleanText($('body').text());
    }

    return { title, author, body, tables: extractTables($) };
}

module.exports = extract;

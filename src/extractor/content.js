const CONTENT_SELECTORS = [
    'article',
    'main',
    '[role="main"]',
    '#js_content',
    '.rich_media_content',
    '.article-content',
    '.post-content',
    '.entry-content',
    '.content'
];

function cleanText(text) {
    return (text || '')
        .replace(/[\u200B-\u200D\uFEFF]/g, '')
        .replace(/[ \t]+\n/g, '\n')
        .replace(/\n{3,}/g, '\n\n')
        .trim();
}

function extractTitle($) {
    const ogTitle = $('meta[property="og:title"]').attr('content');
    if (ogTitle && ogTitle.trim()) return ogTitle.trim();

    const selectors = ['h1', '#activity-name', '.article-title', '.post-title', 'title'];
    for (const selector of selectors) {
        const value = $(selector).first().text().trim();
        if (value) return value;
    }
    return '';
}

function extractAuthor($) {
    const selectors = [
        'meta[name="author"]',
        'meta[property="article:author"]',
        '#js_name',
        '.author',
        '.byline'
    ];
    for (const selector of selectors) {
        const node = $(selector).first();
        const value = (node.attr('content') || node.text() || '').trim();
        if (value) return value;
    }
    return '';
}

function extractMainContent($, title) {
    for (const selector of CONTENT_SELECTORS) {
        const node = $(selector).first();
        if (node.length && node.text().trim().length > 200) {
            node.find('script, style, nav, footer, header, aside, .comment, .comments').remove();
            if (title) {
                node.find('h1, h2').each((_, heading) => {
                    if ($(heading).text().trim() === title) {
                        $(heading).remove();
                    }
                });
            }
            return cleanText(node.text());
        }
    }
    $('script, style, nav, footer, header, aside').remove();
    return cleanText($('body').text());
}

function extractTables($) {
    const tables = [];
    $('table').each((_, table) => {
        const rows = [];
        $(table).find('tr').each((_, tr) => {
            const cells = [];
            $(tr).find('th, td').each((_, cell) => {
                cells.push($(cell).text().replace(/\s+/g, ' ').trim());
            });
            if (cells.some(cell => cell.length > 0)) {
                rows.push(cells);
            }
        });
        if (rows.length > 0) {
            tables.push(rows);
        }
    });
    return tables;
}

function extractFromHtml(html) {
    const cheerio = require('cheerio');
    const $ = cheerio.load(html);
    const title = extractTitle($);
    return {
        title,
        author: extractAuthor($),
        body: extractMainContent($, title),
        tables: extractTables($)
    };
}

module.exports = { extractFromHtml, extractTables, cleanText };

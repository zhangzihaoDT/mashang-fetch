function build(raw, url) {
    const title = (raw.title || '').trim() || '无标题文章';
    return {
        title,
        source: url,
        author: (raw.author || '').trim(),
        fetched_at: new Date().toISOString(),
        body: (raw.body || '').trim(),
        tables: Array.isArray(raw.tables) ? raw.tables : []
    };
}

module.exports = { build };

function escapeCell(value) {
    const text = String(value == null ? '' : value);
    if (/[",\n\r]/.test(text)) {
        return `"${text.replace(/"/g, '""')}"`;
    }
    return text;
}

function pickTable(doc) {
    const tables = doc.tables || [];
    for (const table of tables) {
        if (table.length > 0 && table.some(row => row.length > 1)) {
            return table;
        }
    }
    return tables[0] || null;
}

function render(doc) {
    const table = pickTable(doc);
    if (!table) {
        throw new Error('该页面没有可导出的表格数据，请改用 Markdown 格式');
    }
    return table.map(row => row.map(escapeCell).join(',')).join('\n') + '\n';
}

module.exports = { render };

const fs = require('fs');
const path = require('path');
const markdown = require('./markdown');
const csv = require('./csv');

const EXPORTERS = {
    md: { ext: 'md', render: markdown.render },
    csv: { ext: 'csv', render: csv.render }
};

function safeSegment(text) {
    return String(text || '')
        .replace(/[^\p{L}\p{N} _-]/gu, '_')
        .replace(/\s+/g, ' ')
        .trim()
        .slice(0, 50) || 'untitled';
}

function timestamp() {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

function supportedFormats() {
    return Object.keys(EXPORTERS);
}

function exportDocument(doc, format, outDir) {
    const exporter = EXPORTERS[format];
    if (!exporter) {
        throw new Error(`不支持的格式: ${format}（可选: ${supportedFormats().join(', ')}）`);
    }

    const content = exporter.render(doc);
    fs.mkdirSync(outDir, { recursive: true });

    const filename = `${timestamp()}_${safeSegment(doc.title)}.${exporter.ext}`;
    const filePath = path.join(outDir, filename);
    fs.writeFileSync(filePath, content, 'utf8');

    return { path: filePath, filename, format, ext: exporter.ext };
}

module.exports = { exportDocument, supportedFormats };

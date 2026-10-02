function yamlString(value) {
    const text = String(value == null ? '' : value);
    if (text === '' || /[:#\n"']/.test(text)) {
        return `"${text.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, '\\n')}"`;
    }
    return text;
}

function render(doc) {
    const lines = ['---'];
    lines.push(`title: ${yamlString(doc.title)}`);
    lines.push(`source: ${yamlString(doc.source)}`);
    if (doc.author) {
        lines.push(`author: ${yamlString(doc.author)}`);
    }
    lines.push(`fetched_at: ${yamlString(doc.fetched_at)}`);
    lines.push('format: markdown');
    lines.push('---', '');

    let content = lines.join('\n');
    content += `# ${doc.title}\n\n`;
    if (doc.author) {
        content += `> 作者：${doc.author}\n\n`;
    }
    content += doc.body + '\n';

    return content;
}

module.exports = { render };

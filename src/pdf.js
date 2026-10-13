const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const http = require('./http');
const cheerio = require('cheerio');

function pdfTitle(headers, url) {
    const disposition = headers['content-disposition'] || '';
    const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    const plain = disposition.match(/filename="([^"]+)"|filename=([^;]+)/i);
    let name = encoded ? encoded[1] : plain ? (plain[1] || plain[2]).trim() : new URL(url).pathname.split('/').pop();
    try { name = decodeURIComponent(name || 'document'); } catch { /* Keep original name. */ }
    return path.basename(name.replace(/\\/g, '/')).replace(/\.pdf$/i, '')
        .replace(/[^\p{L}\p{N} _-]/gu, '_').trim().slice(0, 80) || 'document';
}

async function downloadPdf(url, outDir, options = {}) {
    const response = await http.get(url, {
        responseType: 'stream',
        validateStatus: status => status >= 200 && status < 300,
        headers: { Accept: 'application/pdf,text/html;q=0.9,*/*;q=0.8', ...(options.source ? { Referer: options.source } : {}) }
    });
    const finalUrl = response.request.res.responseUrl || url;
    if ((response.headers['content-type'] || '').includes('text/html') && !options.attachment) {
        const chunks = [];
        let size = 0;
        try {
            for await (const chunk of response.data) {
                size += chunk.length;
                if (size > 5 * 1024 * 1024) throw new Error('网页过大，无法查找 PDF 附件');
                chunks.push(chunk);
            }
        } finally { response.data.destroy(); }
        const $ = cheerio.load(Buffer.concat(chunks).toString('utf8'));
        let base = finalUrl;
        try { base = new URL($('base[href]').attr('href') || '', finalUrl).href; } catch {}
        const candidates = new Map();
        $('a[href]').each((_, element) => {
            const name = $(element).text().trim() || $(element).attr('title') || '';
            try {
                const target = new URL($(element).attr('href'), base);
                if (!['http:', 'https:'].includes(target.protocol)) return;
                if (!/\.pdf(?:$|[?#])/i.test(target.href) && !/\.pdf$/i.test(name)) return;
                target.hash = '';
                if (!candidates.has(target.href)) candidates.set(target.href, { url: target.href, name: name || pdfTitle({}, target.href) + '.pdf' });
            } catch {}
        });
        const attachments = [...candidates.values()];
        if (!attachments.length) throw new Error('未找到 PDF 附件，请检查页面或提供直接下载链接');
        if (!options.selected && attachments.length > 1) {
            return { ok: true, needs_selection: true, source: url, attachments };
        }
        const selected = options.selected || [attachments[0].url];
        if (!selected.length || selected.some(link => !candidates.has(link))) throw new Error('请选择页面中的 PDF 附件');
        const results = [], failed = [];
        for (const link of [...new Set(selected)]) {
            try {
                results.push(await downloadPdf(link, outDir, { source: url, name: candidates.get(link).name, attachment: true }));
            } catch (error) { failed.push({ url: link, name: candidates.get(link).name, error: error.message }); }
        }
        return { ok: results.length > 0, error: results.length ? undefined : failed.map(item => item.error).join('；'), results, failed };
    }
    let temporary;
    let handle;
    try {
        const title = pdfTitle(options.name ? { 'content-disposition': `attachment; filename="${options.name.replace(/"/g, '')}"` } : response.headers, finalUrl);
        fs.mkdirSync(outDir, { recursive: true });
        const filename = `${new Date().toISOString().replace(/[-:]/g, '').replace(/T/, '_').slice(0, 15)}_${title}_${crypto.randomBytes(4).toString('hex')}.pdf`;
        const filePath = path.join(outDir, filename);
        temporary = `${filePath}.part`;
        handle = await fs.promises.open(temporary, 'wx');
        let prefix = Buffer.alloc(0);
        let validated = false;
        for await (const chunk of response.data) {
            if (!validated) {
                prefix = Buffer.concat([prefix, chunk]);
                if (prefix.length < 5) continue;
                if (prefix.subarray(0, 5).toString('ascii') !== '%PDF-') {
                    throw new Error('链接返回的内容不是 PDF，请提供 PDF 文件的直接下载链接');
                }
                validated = true;
                await handle.writeFile(prefix);
                prefix = null;
            } else {
                await handle.writeFile(chunk);
            }
        }
        if (!validated) throw new Error('PDF 文件为空或不完整');
        await handle.close();
        handle = null;
        await fs.promises.rename(temporary, filePath);
        const meta = { title, source: options.source || url, download_url: finalUrl, fetched_at: new Date().toISOString() };
        await fs.promises.writeFile(path.join(outDir, `.${filename}.source.json`), JSON.stringify(meta), 'utf8');
        return { ok: true, path: filePath, filename, format: 'pdf', strategy: 'pdf',
            meta };
    } catch (error) {
        response.data.destroy();
        if (handle) await handle.close();
        if (temporary) await fs.promises.rm(temporary, { force: true });
        throw error;
    }
}

module.exports = { downloadPdf };

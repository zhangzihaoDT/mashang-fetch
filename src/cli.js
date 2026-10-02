#!/usr/bin/env node
const path = require('path');
const resolver = require('./resolver');
const extractor = require('./extractor');
const normalizer = require('./normalizer');
const exporter = require('./exporter');

// 所有进度日志走 stderr，stdout 只输出最终 JSON 结果
console.log = (...args) => console.error(...args);

function parseArgs(argv) {
    const args = { url: '', format: 'md', out: '' };
    for (let i = 0; i < argv.length; i++) {
        const arg = argv[i];
        if (arg === '--format' || arg === '-f') {
            args.format = argv[++i];
        } else if (arg === '--out' || arg === '-o') {
            args.out = argv[++i];
        } else if (arg === '--help' || arg === '-h') {
            args.help = true;
        } else if (!arg.startsWith('-') && !args.url) {
            args.url = arg;
        }
    }
    return args;
}

function emit(payload, ok) {
    process.stdout.write(JSON.stringify(payload) + '\n');
    if (!ok) {
        process.exitCode = 1;
    }
}

async function main() {
    const args = parseArgs(process.argv.slice(2));

    if (args.help || !args.url) {
        emit({
            ok: false,
            error: '用法: node src/cli.js <url> --format md|csv [--out DIR]'
        }, false);
        return;
    }

    const { url, strategy } = resolver.resolve(args.url);
    const raw = await extractor.run(strategy, url);
    const doc = normalizer.build(raw, url);

    const outDir = args.out
        ? path.resolve(args.out)
        : path.resolve(__dirname, '..', 'output');
    const result = exporter.exportDocument(doc, args.format, outDir);

    emit({
        ok: true,
        path: result.path,
        filename: result.filename,
        format: result.format,
        strategy,
        meta: {
            title: doc.title,
            author: doc.author,
            source: doc.source,
            fetched_at: doc.fetched_at,
            tables: doc.tables.length
        }
    }, true);
}

main().catch(error => {
    emit({ ok: false, error: error.message || String(error) }, false);
});

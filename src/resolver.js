const WECHAT_HOST = 'mp.weixin.qq.com';

function normalizeUrl(input) {
    if (!input || typeof input !== 'string') {
        throw new Error('无效的URL格式，URL必须以http://或https://开头');
    }
    let url = input.trim();
    if (!/^https?:\/\//i.test(url)) {
        throw new Error('无效的URL格式，URL必须以http://或https://开头');
    }
    return url;
}

function classify(url) {
    let host;
    try {
        host = new URL(url).hostname.toLowerCase();
    } catch (e) {
        throw new Error(`无法解析URL: ${url}`);
    }
    if (host === WECHAT_HOST || host.endsWith('.' + WECHAT_HOST)) {
        return 'wechat';
    }
    return 'dynamic';
}

function resolve(input) {
    const url = normalizeUrl(input);
    return { url, strategy: classify(url) };
}

module.exports = { resolve, normalizeUrl, classify };

const wechat = require('./wechat');
const dynamic = require('./dynamic');

const STRATEGIES = {
    wechat,
    dynamic
};

async function run(strategy, url) {
    const extractor = STRATEGIES[strategy];
    if (!extractor) {
        throw new Error(`未知的抓取策略: ${strategy}`);
    }
    const result = await extractor(url);
    if (!result.body) {
        throw new Error('未能从页面提取到正文内容');
    }
    return result;
}

module.exports = { run };

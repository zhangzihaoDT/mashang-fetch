const axios = require('axios');

const defaultProxyConfig = null;

const instance = axios.create({
    timeout: 180000,
    maxRedirects: 15,
    proxy: defaultProxyConfig,
    proxyErrorHandler: async (err) => {
        console.error('代理连接错误:', err.message);
        if (defaultProxyConfig && err.code === 'ECONNREFUSED') {
            if (defaultProxyConfig.retries > 0) {
                console.log(`代理连接失败，剩余重试次数: ${defaultProxyConfig.retries}`);
                defaultProxyConfig.retries--;
                await new Promise(resolve => setTimeout(resolve, 2000));
                return instance(err.config);
            }
            console.error(`无法连接到代理服务器 ${defaultProxyConfig.host}:${defaultProxyConfig.port}，请确保代理服务正在运行`);
        }
        throw err;
    },
    headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, compress, deflate, br',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1'
    },
    validateStatus: function (status) {
        return status >= 200 && status < 500;
    },
    retry: 5,
    retryDelay: (retryCount) => Math.min(1000 * Math.pow(2, retryCount), 10000),
    retryCondition: (error) => {
        if (axios.isAxiosError(error)) {
            console.log(`请求失败，准备重试。错误类型: ${error.code}`);
            if (error.response) {
                console.log(`响应状态: ${error.response.status}`);
            }
            return (
                error.code === 'ECONNABORTED' ||
                error.code === 'ECONNREFUSED' ||
                error.code === 'ECONNRESET' ||
                error.code === 'ETIMEDOUT' ||
                (error.response && error.response.status >= 500)
            );
        }
        return false;
    }
});

module.exports = instance;

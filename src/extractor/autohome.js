const cheerio = require('cheerio');

function isComparison(url) {
    const parsed = new URL(url);
    return parsed.hostname === 'car.autohome.com.cn' && /^\/duibi\/chexing\/?$/.test(parsed.pathname);
}

function extractComparison(html, url) {
    const $ = cheerio.load(html);
    const ids = new URLSearchParams(new URL(url).hash.slice(1)).get('carids')?.split(',').filter(Boolean) || [];
    const columns = [];
    $('.compare-choice .compare-name').each((index, el) => {
        const link = $(el).find('p').first().find('a').first();
        const name = link.text().trim();
        const id = (link.attr('href') || '').match(/\/spec\/(\d+)/)?.[1];
        if (name && id && !columns.some(column => column.id === id)) columns.push({ index, name, id });
    });
    if (!columns.length || ids.some(id => !columns.some(column => column.id === id))) {
        throw new Error('汽车之家车型对比未加载完整，或页面需要验证，请稍后重试');
    }
    const table = [['分类', '参数', ...columns.map(column => column.name)]];
    $('.compare-content__box').each((_, box) => {
        const category = $(box).children('.compare-content__tit').text().trim();
        $(box).find('.compare-content__item').each((_, row) => {
            const label = $(row).children('.title-cell').text().replace(/\s+/g, ' ').trim();
            if (!label) return;
            const cells = $(row).children('.content-cell');
            if (columns.some(column => !cells.eq(column.index).length)) {
                throw new Error('汽车之家车型对比列不完整，请稍后重试');
            }
            const values = columns.map(column => {
                const cell = cells.eq(column.index).clone();
                cell.find('.icons-standard').replaceWith(' [标配] ');
                cell.find('.icons-select').replaceWith(' [选配] ');
                cell.find('.athm-btn, .calculators-icon').remove();
                cell.find('p').append('；');
                return cell.text().replace(/\s+/g, ' ').trim().replace(/；$/, '') || '未提供';
            });
            table.push([category, label, ...values]);
        });
    });
    if (table.length < 2) throw new Error('汽车之家车型参数尚未加载，请稍后重试');
    const escape = value => value.replace(/\|/g, '\\|').replace(/\n/g, '<br>');
    const body = '配置状态：[标配]、[选配]；- 表示无，未提供表示页面为空。参数仅供参考，以实际销售车辆为准。\n\n'
        + table.map((row, index) => '| ' + row.map(escape).join(' | ') + ' |'
            + (index === 0 ? '\n| ' + row.map(() => '---').join(' | ') + ' |' : '')).join('\n');
    return { title: columns.map(column => column.name).join(' 对比 '), body, tables: [table] };
}

module.exports = { isComparison, extractComparison };

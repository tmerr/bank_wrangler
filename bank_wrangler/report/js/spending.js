window.spendingByCategory = function spendingByCategory(model, minMs, maxMs) {
    const categoryColumn = model.columns.indexOf('category');
    const amountColumn = model.columns.indexOf('amount');
    const fromColumn = model.columns.indexOf('from');
    const toColumn = model.columns.indexOf('to');
    const dateColumn = model.columns.indexOf('date');
    const result = new Map();
    model.transactions
         .filter(t => {
             const from = t[fromColumn];
             const to = t[toColumn];
             return model.accounts.includes(from) && !model.accounts.includes(to);
         })
         .filter(t => {
             if (minMs === undefined) {
                 return true;
             } else {
                 const ms = dateToMs(t[dateColumn]);
                 return minMs <= ms && ms <= maxMs;
             }
         })
         .forEach(t => {
             const category = t[categoryColumn];
             const amount = parseFloat(t[amountColumn]);
             if (result.has(category)) {
                 // round to 2 decimal places
                 result.set(category, Math.round(100*(result.get(category) + amount))/100);
             } else {
                 result.set(category, amount);
             }
         });
    if (result.has('')) {
        result.set('Uncategorized', result.get(''));
        result.delete('');
    }
    return result;
};

const doughnutData = function doughnutData(spending) {
    const chartColors = [
        'rgb(255, 99, 132)',
        'rgb(255, 159, 64)',
        'rgb(255, 205, 86)',
        'rgb(75, 192, 192)',
        'rgb(54, 162, 235)',
        'rgb(153, 102, 255)',
        'rgb(201, 203, 207)'
    ];

    return {
        datasets: [{
            data: Array.from(spending.values()),
            backgroundColor: Array.from(spending.keys()).map(
                (col, i) => chartColors[i % chartColors.length]
            ),
            label: 'Whatever',
        }],
        labels: Array.from(spending.keys()),
    }
};

window.doughnutConfig = function doughnutConfig(spending) {
    return {
        type: 'doughnut',
        data: doughnutData(spending),
    };
};

/**
 * Convert a bank-wrangler style date to a numeric value in milliseconds
 * using Date.getTime.
 */
const dateToMs = function dateToMs(date) {
    const [year, month, day] = date.split('/').map(s => parseInt(s));
    return (new Date(year, month, day)).getTime();
};

/**
 * Convert a numeric value in milliseconds to a bank-wrangler style date.
 */
const msToDate = function msToDate(ms) {
    const date = new Date(ms);
    const triplet = [date.getFullYear(), date.getMonth(), date.getDate()];
    return triplet.join('/');
};

window.sliderConfig = function sliderConfig(model) {
    const dateColumn = model.columns.indexOf('date');
    const datesInMs = model.transactions.map(t => dateToMs(t[dateColumn]));
    const minMs = Math.min(...datesInMs);
    const maxMs = Math.max(...datesInMs);

    // Use one day steps.
    const step = 24 * 60 * 60 * 1000;

    return {
        start: [minMs, maxMs],
        connect: true,
        step: step,
        range: {
            'min': [ minMs ],
            'max': [ maxMs ],
        },
    };
};

window.connectSliderToDisplays = function connectSliderToDisplays(slider, displaylow, displayhigh) {
    slider.noUiSlider.on('update', function(values, handle) {
        const selected = [displaylow, displayhigh][handle];
        selected.innerHTML = msToDate(parseInt(values[handle]));
    });
};

window.connectSliderToChart = function connectSliderToChart(slider, chart, model) {
    slider.noUiSlider.on('set', function(values, handle) {
        const low = values[0];
        const high = values[1];
        const spending = window.spendingByCategory(model, low, high);
        chart.data = doughnutData(spending);
        chart.update(0);
    });
};

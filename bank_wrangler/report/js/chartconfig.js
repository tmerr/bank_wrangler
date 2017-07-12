'use strict';

const dates = function dates(model) {
    const dateColumn = model.columns.indexOf('date');
    const set = new Set();
    model.transactions.forEach(transaction => {
        set.add(transaction[dateColumn]);
    });
    const result = [...set];
    result.sort();
    return result;
};

const deltaAmounts = function deltaAmounts(model, account) {
    const toColumn = model.columns.indexOf('to');
    const fromColumn = model.columns.indexOf('from');
    const dateColumn = model.columns.indexOf('date');
    const amountColumn = model.columns.indexOf('amount');
    const map = new Map();
    dates(model).forEach(date => {
        map.set(date, 0.0);
    });
    model.transactions.forEach(transaction => {
        const date = transaction[dateColumn];
        const amount = parseFloat(transaction[amountColumn]);
        if (account === transaction[toColumn]) {
            map.set(date, map.get(date) + amount);
        } else if (account === transaction[fromColumn]) {
            map.set(date, map.get(date) - amount);
        }
    });
    return Array.from(map.values());
};

const cumulativeAmounts = function cumulativeAmounts(deltaAmounts) {
    const result = [];
    let rollingsum = 0.0;
    deltaAmounts.forEach(delta => {
        // round to 2 decimal places
        rollingsum = Math.round(100*(rollingsum + delta))/100;
        result.push(rollingsum);
    });
    return result;
};

window.chartConfig = function chartConfig(model) {
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
        type: 'line',
        data: {
            labels: dates(model),
            datasets: model.accounts.map((account, index) => {
                return {
                    label: account,
                    borderColor: chartColors[index % chartColors.length],
                    backgroundColor: chartColors[index % chartColors.length],
                    data: cumulativeAmounts(deltaAmounts(model, account)),
                }
            })
        },
        options: {
            scales: {
                yAxes: [{
                    stacked: true
                }]
            },
            elements: {
                line: {
                    tension: 0
                },
                point: {
                    radius: 0,
                    hitRadius: 10,
                    hoverRadius: 5
                }
            }
        }
    };
};

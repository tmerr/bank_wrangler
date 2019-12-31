from collections import defaultdict
from bank_wrangler.schema import Transaction


def stitch(transactions_by_account):
    result = []
    needs_match = defaultdict(list)
    for acct, ts in transactions_by_account.items():
        for t in ts:
            try:
                k = (t.source, t.to, t.date, t.amount)
                if k in needs_match:
                    matches = needs_match[k]
                    (matchact, match) = matches.pop()
                    if len(matches) == 0:
                        del needs_match[k]
                    result.append(Transaction(
                        'placeholder',
                        t.source,
                        t.to,
                        t.date,
                        '{} + {}'.format(t.description, match.description),
                        t.amount,
                        t.category,
                    ))
                    continue
            except IndexError:
                pass
            if t.source == acct:
                other = t.to
            elif t.to == acct:
                other = t.source
            else:
                raise ValueError('transaction {} in account {} has unexpected parties'.format(t, acct))
            if other == '':
                result.append(t)
                continue
            if other not in transactions_by_account:
                raise ValueError('transaction {} references an unknown account {}'.format(t, other))
            needs_match[(t.source, t.to, t.date, t.amount)].append((acct, t))
    for ts in needs_match.values():
        for (acct, t) in ts:
            # a transaction with another party involved needs a corresponding
            # transaction with opposite direction. if it does not exist, remove
            # the reference to the other account and make not of it.
            fmt = t.description + ' [missing corresponding txn in {}]'
            if t.source == acct:
                t = t._replace(to='', description=fmt.format(t.to))
            elif t.to == acct:
                t = t._replace(source='', description=fmt.format(t.source))
            else:
                assert False
            result.append(t)
    return result

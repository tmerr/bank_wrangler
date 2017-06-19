from itertools import zip_longest, chain
from collections import defaultdict
from bank_wrangler import schema


def _get_field(transaction, column_name):
    keys = list(schema.COLUMNS)
    i = keys.index(column_name)
    return transaction[i]


def _partition(iterable, key):
    """partition into sublists by key"""
    bykey = defaultdict(list)
    for elem in iterable:
        bykey[key(elem)].append(elem)
    return dict(bykey)


def _loose_identity(transaction):
    return tuple(_get_field(transaction, col)
                 for col in ('from', 'to', 'date', 'amount'))


def _fuse(transA, transB):
    bankA, frmA, toA, dateA, descriptionA, amountA = transA
    bankB, frmB, toB, dateB, descriptionB, amountB = transB
    assert _loose_identity(transA) == _loose_identity(transB)
    if descriptionA == descriptionB:
        new_description = descriptionA
    else:
        new_description = schema.String('{} + {}'.format(
            descriptionA.value,
            descriptionB.value
        ))
    return (
        schema.String('{} + {}'.format(bankA.value, bankB.value)),
        frmA,
        toA,
        dateA,
        new_description,
        amountA
    )


def _unmatch(trans, source_accounts):
    bank, frm, to, date, description, amount = trans
    def rewrite(account):
        if account.value in source_accounts:
            return account
        else:
            return schema.String('unmatched: {}'.format(account))
    return (
        bank,
        *map(rewrite, [frm, to]),
        date,
        description,
        amount
    )


def _split_internal_external(transactions, accounts_set):
    def isinternal(transaction):
        frm = _get_field(transaction, 'from').value
        to = _get_field(transaction, 'to').value
        return frm in accounts_set and to in accounts_set
    internal = [t for t in transactions if isinternal(t)]
    external = [t for t in transactions if not isinternal(t)]
    return (internal, external)


def deduplicate(transactions, bank_to_accounts_map):
    """
    Whenever money changes hands between two known banks, we should see nearly
    identical transactions originating from both sources. Ensure these pairs of
    transactions exist and fuse them together. If there are stray transactions,
    change either the "from" or "to" (depending) to "unmatched: <old value>",
    since this helps keep balances intact.

    * If the user fails to properly set a TO/FROM for both bank soures
      in the rules file they would see something like this:

      accountA                  wrong-account-name-B
      o-----------$500-------------> o
      o-----------$500-------------> o
      wrong-account-name-A      accountB

      This represents two external transactions.

    * If the user correctly sets a TO/FROM for one bank but not the other
      they should see:

      accountA                  wrong-account-name-B
      o-----------$500-------------> o
      o-----------$500-------------> o
      unmatched: accountA       accountB

      Once again balances are left intact.

    * If only one bank has the transaction on record:

      accountA                  unmatched: accountB
      o------------$500------------> o

      By marking accountB as unmatched we avoid magically inject money
      into accountB. The bank responsible for accountB should have already
      made sure its transactions add up to the correct balance, inserting
      a dummy "initial balance" transaction if necessary (because it only
      goes back so far). accountA should not interfere.

    * If the user sets both correctly we should see:

      accountA                  accountB
      o------------$500------------> o
    """
    internal_transactions, external_transactions = _split_internal_external(
        transactions,
        set(chain(*bank_to_accounts_map.values()))
    )
    result = schema.TransactionModel(schema.COLUMNS)
    for similar in _partition(internal_transactions, key=_loose_identity).values():
        splitbybank = list(_partition(similar,
                                      key=lambda t: _get_field(t, 'bank')).items())
        assert len(splitbybank) in [1, 2]
        if len(splitbybank) == 1:
            splitbybank.append((None, []))
        (banknameA, tsA), (banknameB, tsB) = splitbybank
        for tA, tB in zip_longest(tsA, tsB):
            if tA is None:
                toadd = _unmatch(tB, bank_to_accounts_map[banknameB.value])
            elif tB is None:
                toadd = _unmatch(tA, bank_to_accounts_map[banknameA.value])
            else:
                toadd = _fuse(tA, tB)
            result.ingest_row(*toadd)

    for t in external_transactions:
        result.ingest_row(*t)

    return result
import argparse
import csv
import itertools
import urllib.error
import urllib.request


def _urlopen(url):
    try:
        return urllib.request.urlopen(url)
    except urllib.error.HTTPError:
        return None


def do_marks(args):
    marks_iter = marks(args.urltemplate, args.startroll, args.endroll)
    with open(args.output, 'w', newline='') as f:
        w = csv.writer(f)
        colnames = None
        try:
            for colnames, row in marks_iter:
                w.writerow(row)
                print(row)
        except KeyboardInterrupt:
            pass
        finally:
            if colnames is not None:
                w.writerow(colnames)
                print(colnames)


def marks(urltemplate, startroll, endroll=None):
    if endroll is not None and startroll > endroll:
        raise ValueError('startroll > endroll')

    import pandas

    def data(url, roll):
        ROLL_COLUMN_NAME = 'Roll'

        response = _urlopen(url)
        if not response:
            return {ROLL_COLUMN_NAME: roll, '<Error>': 'Error'}

        table = pandas.read_html(response, keep_default_na=False)[0]
        table = table.to_numpy()

        def data_meta(table):
            d = {}
            for cell in itertools.chain.from_iterable(table):
                if ':' in cell:
                    key, value = cell.split(':', 1)
                    if 'roll' in key.lower():
                        key = ROLL_COLUMN_NAME
                    d[key] = value
            return d

        def data_marks(table):
            header_indices = []
            for i, row in enumerate(table):
                if 'course' in row[0].lower():
                    header_indices.append(i)

            hstart = header_indices[0]
            hend = header_indices[-1]

            # remove data cells that overflow into header
            header_rows = table[hstart:hend+1]
            for i, cell in enumerate(header_rows[-1]):
                if table[hend+1][i] == cell:
                    header_rows[-1][i] = '<removed>'

            flat_header = [' >> '.join(header_cells) for header_cells in zip(*header_rows)]

            tend = None
            for i, row in enumerate(table[hend+1:], start=hend+1):
                if len(set(row)) == 1:
                    tend = i
                    break

            d = {}
            for row in table[hend+1:tend]:
                key = row[0]
                for hdr, cell in zip(flat_header, row):
                    d[key + ' >> ' + hdr] = cell

            return d

        return data_meta(table) | data_marks(table)

    colnames = []
    roll = startroll - 1
    while roll != endroll:
        roll += 1
        d = data(urltemplate.format(roll), roll)
        row = [d.pop(c, '') for c in colnames]
        colnames.extend(d.keys())
        row.extend(d.values())
        yield colnames, row


def do_exams(args):
    exams_iter = exams('https://result.pup.ac.in', args.search)
    try:
        for examname, urltemplate in exams_iter:
            print(examname)
            print('\t', urltemplate or 'error')
    except KeyboardInterrupt:
        pass


def exams(homepage_url, search=None):
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import NoSuchElementException

    options = webdriver.EdgeOptions()
    options.add_argument('headless')

    with webdriver.Edge(options=options) as driver:
        driver.get(homepage_url)
        search = search or ''
        aid_list = [a.get_attribute('id')
                    for a in driver.find_elements(By.TAG_NAME, 'a')
                    if search in a.text]

        for aid in aid_list:
            driver.get(homepage_url)
            a = driver.find_element(By.ID, aid)
            examname = a.text
            a.click()
            try:
                entry = driver.find_element(By.ID, 'MainContent_txtRegNumw')
            except NoSuchElementException:
                yield examname, None
                continue
            TRIAL_ROLL = '123456'
            entry.send_keys(TRIAL_ROLL)
            entry.send_keys(Keys.RETURN)
            driver.switch_to.window(driver.window_handles[-1])
            urltemplate = driver.current_url.replace(TRIAL_ROLL, '{}')
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            yield examname, urltemplate


def do_rolls(args):
    validrolls = []
    rolls_iter = rolls(args.urltemplate, args.test_rolls, args.test_ranges)
    try:
        for roll, isvalid in rolls_iter:
            print(roll, 'valid' if isvalid else '')
            if isvalid:
                validrolls.append(roll)
    except KeyboardInterrupt:
        pass
    finally:
        print(validrolls if validrolls else 'no valid rolls found')


def rolls(urltemplate, test_rolls=None, test_ranges=None):
    test_rolls = test_rolls or ()
    test_ranges = [range(startroll, endroll + 1)
                   for startroll, endroll
                   in test_ranges or ()]

    for roll in itertools.chain(test_rolls, *test_ranges):
        yield roll, bool(_urlopen(urltemplate.format(roll)))


parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()

parser_marks = subparsers.add_parser('marks')
parser_marks.add_argument('urltemplate')
parser_marks.add_argument('startroll', type=int)
parser_marks.add_argument('endroll', type=int, nargs='?')
parser_marks.add_argument('--output', '-o', default='pumarks.csv')
parser_marks.set_defaults(func=do_marks)

parser_exams = subparsers.add_parser('exams')
parser_exams.add_argument('--search')
parser_exams.set_defaults(func=do_exams)

parser_rolls = subparsers.add_parser('rolls')
parser_rolls.add_argument('urltemplate')
parser_rolls.add_argument('--rolls', type=int, nargs='+', dest='test_rolls',
                          metavar='ROLL')
parser_rolls.add_argument('--range', type=int, nargs=2, action='append',
                          dest='test_ranges', metavar=('STARTROLL', 'ENDROLL'))
parser_rolls.set_defaults(func=do_rolls)


if __name__ == '__main__':
    args = parser.parse_args()
    args.func(args)

import argparse
import csv
import itertools
import urllib.error
import urllib.request


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
        ROLLCOLNAME = 'Roll'
        DATA_ABSPOS = (
            (ROLLCOLNAME,   ( 7, 14), lambda s: s[s.find(':')+1: ].strip()),
            ('College',     ( 5, 14), lambda s: s[s.find(':')+1: ].strip()),
            ('Honours',     ( 5,  0), lambda s: s[s.find('(')+1: s.find(')')]),
            ('Name',        ( 7,  0), lambda s: s[s.find(':')+1: ].strip().title()),
            ('SGPA',        (11, 11), None),
            ('Result',      (11, 12), None),
            ('CGPA',        (11, 13), None),
            ('Status',      (11, 14), None),
        )
        ERRCOLNAME = DATA_ABSPOS[1][0]

        def data_abspos(table):
            d = {}
            for colname, (nrow, ncol), fmtfunc in DATA_ABSPOS:
                text = table.at[nrow, ncol]
                if fmtfunc:
                    text = fmtfunc(text)
                d[colname] = text
            return d

        ROWSTART = 12
        COLCODE = 0
        COLGRADE = 8
        ENDMARKER = 'Total'

        def data_relpos(table):
            d = {}
            r = ROWSTART
            while True:
                code = table.at[r, COLCODE]
                if code.strip() == ENDMARKER:
                    break
                grade = table.at[r, COLGRADE]
                d[code] = grade
                r += 1
            return d

        try:
            table = pandas.read_html(url, keep_default_na=False)[0]
        except urllib.error.HTTPError as e:
            return {ROLLCOLNAME: roll, ERRCOLNAME: e}
        return data_abspos(table) | data_relpos(table)

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
    try:
        for roll, isvalid in rolls(args.urltemplate, args.test_rolls,
                                   args.test_ranges):
            print(roll)
            if isvalid:
                validrolls.append(roll)
                print('\tvalid')
    except KeyboardInterrupt:
        pass
    finally:
        print(validrolls if validrolls else '\nno valid rolls found')


def rolls(urltemplate, test_rolls=None, test_ranges=None):
    def isvalid(roll):
        try:
            urllib.request.urlopen(urltemplate.format(roll))
        except urllib.error.HTTPError:
            return False
        else:
            return True

    test_rolls = test_rolls or ()
    test_ranges = [range(startroll, endroll + 1)
                   for startroll, endroll
                   in test_ranges or ()]

    for roll in itertools.chain(test_rolls, *test_ranges):
        yield roll, isvalid(roll)


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

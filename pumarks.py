import argparse
import csv
import urllib.error
import pandas

parser = argparse.ArgumentParser()
parser.add_argument('urltemplate')
parser.add_argument('startroll', type=int)
parser.add_argument('endroll', type=int, nargs='?')
parser.add_argument('--output', '-o', default='pumarks.csv')

def main(args):
    marks = pumarks(args.urltemplate, args.startroll, args.endroll)
    with open(args.output, 'w', newline='') as f:
        w = csv.writer(f)
        colnames = None
        try:
            for colnames, row in marks:
                w.writerow(row)
        except KeyboardInterrupt:
            pass
        finally:
            if colnames is not None:
                w.writerow(colnames)

def pumarks(urltemplate, startroll, endroll):
    colnames = []
    roll = startroll - 1
    while roll != endroll:
        roll += 1
        d = data(urltemplate.format(roll), roll)
        row = [d.pop(c, '') for c in colnames]
        colnames.extend(d.keys())
        row.extend(d.values())
        yield colnames, row

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
ROWSTART = 12
COLCODE = 0
COLGRADE = 8
ENDMARKER = 'Total'

def data(url, roll):
    def data_abspos(table):
        d = {}
        for colname, (nrow, ncol), fmtfunc in DATA_ABSPOS:
            text = table.at[nrow, ncol]
            if fmtfunc:
                text = fmtfunc(text)
            d[colname] = text
        return d

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
    d = data_abspos(table)
    d.update(data_relpos(table))
    return d

if __name__ == '__main__':
    main(parser.parse_args())

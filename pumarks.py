import argparse
import csv
import itertools
import urllib.error
import urllib.request


def main(args):
    rolls = args.rolls or []
    roll_ranges = [range(startroll, endroll + 1)
                   for startroll, endroll in (args.roll_ranges or [])]
    rolls_counter = (itertools.count(args.start_roll)
                     if args.start_roll else [])
    marks_iter = pumarks(
        args.urltemplate,
        itertools.chain(rolls, *roll_ranges, rolls_counter))
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


def pumarks(urltemplate, rolls):
    import pandas

    def data(url, roll):
        def data_meta(table):
            d = {}
            for cell in itertools.chain.from_iterable(table):
                if ':' in cell:
                    key, value = cell.split(':', 1)
                    if 'roll' in key.lower():
                        key = ROLL_COLUMN_NAME
                    d[key] = value.strip()
            return d

        def data_marks(table):
            header_indices = []
            for i, row in enumerate(table):
                if 'course' in row[0].lower():
                    header_indices.append(i)
            hstart = header_indices[0]
            hend = header_indices[-1]
            header_rows = table[hstart:hend+1]
            for i, cell in enumerate(header_rows[-1]):
                if table[hend+1][i] == cell:
                    header_rows[-1][i] = '<removed>'
            flat_header = [' >> '.join(header_cells)
                           for header_cells in zip(*header_rows)]
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

        ROLL_COLUMN_NAME = 'Roll'
        try:
            response = urllib.request.urlopen(url)
        except urllib.error.HTTPError as e:
            return {ROLL_COLUMN_NAME: roll, '<Error>': e}
        table = pandas.read_html(response, keep_default_na=False)[0]
        table = table.to_numpy()
        return data_meta(table) | data_marks(table)

    colnames = []
    for roll in rolls:
        d = data(urltemplate.format(roll), roll)
        row = [d.pop(c, '') for c in colnames]
        colnames.extend(d.keys())
        row.extend(d.values())
        yield colnames, row


parser = argparse.ArgumentParser()
parser.add_argument('urltemplate')
parser.add_argument('--output', '-o', default='pumarks.csv')
parser.add_argument('--start', type=int, dest='start_roll')
parser.add_argument('--rolls', type=int, nargs='+', dest='rolls',
                    metavar='ROLL')
parser.add_argument('--range', type=int, nargs=2, action='append',
                    dest='roll_ranges', metavar=('STARTROLL', 'ENDROLL'))


if __name__ == '__main__':
    main(parser.parse_args())

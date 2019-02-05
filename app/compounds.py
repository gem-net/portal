import re
from datetime import datetime
from collections import OrderedDict
import logging

import pandas as pd
from werkzeug.urls import url_quote_plus

from .drive import file_tree_to_df
from .decorators import asynch


logger = logging.getLogger(__name__)

DOC_EXT_LIST = ['doc', 'docx', 'pdf']
DOC_MIMES = ['application/vnd.google-apps.document',
             'application/pdf']

SUMMARY_COL_DICT = OrderedDict([
    ('categ', ('Category', False, 100)),
    ('compound', ('Compound', True, 200)),
    ('cas', ('CAS', True, 100)),
    ('mass', ('Available', True, 80)),
    ('date', ('Modified', True, 100)),
    ('n_docs', ('#Docs', True, 65)),
    ('n_data', ('#Data', True, 65)),
    ('data_exts', ('Extensions', True, 100)),
    ('last_user', ('Modified by', True, 200)),
    ('doc_url', ('doc_url', False, 100)),
    ('doc_mime', ('doc_mime', False, 100)),
    ('doc_title', ('doc_title', False, 200)),
    ('compound_safe', ('compound_safe', False, 200))
    ])

SINGLE_COL_DICT = OrderedDict([
    ('categ', ('Category', 'overview', 100)),
    ('cas', ('CAS', 'overview', 100)),
    ('compound', ('compound', pd.np.nan, 100)),
    ('mass', ('Available', 'overview', 100)),
    ('title', ('Title', 'single', 100)),
    ('date', ('Modified', 'single', 100)),
    ('is_top_dir', ('is_top_dir', pd.np.nan, 100)),
    ('is_data', ('is_data', pd.np.nan, 100)),
    ('is_doc', ('is_doc', pd.np.nan, 100)),
    ('ext', ('Extension', 'single', 100)),
    ('path', ('path', pd.np.nan, 100)),
    ('date_created', ('Created', pd.np.nan, 100)),
    ('date_modified', ('Modified', 'single', 100)),
    ('icon', ('icon', pd.np.nan, 100)),
    ('id', ('id', pd.np.nan, 100)),
    ('is_folder', ('is_folder', pd.np.nan, 100)),
    ('kind', ('kind', pd.np.nan, 100)),
    ('last_user', ('Modified by', 'single', 100)),
    ('mimeType', ('mimeType', pd.np.nan, 100)),
    ('thumb', ('thumb', pd.np.nan, 100)),
    ('trashed', ('trashed', pd.np.nan, 100)),
    ('url_content', ('url_content', pd.np.nan, 100)),
    ('url_view', ('url_view', pd.np.nan, 100)),
    ('compound_safe', ('compound_safe', pd.np.nan, 100)),
])


COMPOUNDS = dict()

# @TODO: set max depth. get path as list rather than string.


def parse_path(path):
    """Extract data attributes from directory names."""
    path_dirs = path.split(' > ')
    is_top_dir = True if len(path_dirs) < 4 else False
    categ = path_dirs[1]
    p_name = path_dirs[2]
    cas = re.match('([\d-]+)_*', p_name).groups()[0]
    rest = p_name[len(cas) + 1:]  # compound_mass_date
    mass, datestr = rest.split('_')[-2:]
    compound = rest.split('_')[:-2]
    compound = '_'.join(compound)
    date = datetime.strptime(datestr, '%Y%m%d').date()
    return categ, cas, compound, mass, date, is_top_dir


def interpret_row(r):
    ext, is_data, is_doc = pd.np.nan, False, False
    is_folder = r.is_folder
    if not is_folder:
        try:
            ext = r.title.split('.')[-1]
        except IndexError:
            pass
        if r.mimeType in DOC_MIMES or ext in DOC_EXT_LIST:
            is_doc = True
        else:
            is_data = True
    return is_data, is_doc, ext


def get_last_user(d):
    doc_users = d.loc[d.is_doc]
    if len(doc_users):
        doc_users = doc_users.sort_values('date_modified', ascending=False)
        last_user = doc_users['last_user'].iloc[0]
        return last_user
    return pd.np.nan


def load_prebuilt_listing():
    """Populate module-level COMPOUNDS dictionary from prebuilt listing."""
    global COMPOUNDS
    from flask import current_app
    compounds_pickle = current_app.config['COMPOUNDS_PICKLE']

    df = pd.read_pickle(compounds_pickle)

    categ, cas, compound, mass, date, is_top_dir = \
        zip(*df.path.apply(parse_path).values)
    meta_a = pd.DataFrame({'categ': categ, 'cas': cas, 'compound': compound,
                           'mass': mass, 'date': date, 'is_top_dir': is_top_dir
                           })
    is_data, is_doc, ext = zip(*df.apply(interpret_row, axis=1).values)
    meta_b = pd.DataFrame({'is_data': is_data, 'is_doc': is_doc, 'ext': ext})

    c = pd.concat([meta_a, meta_b, df], axis=1)
    c['compound_safe'] = c['compound'].apply(url_quote_plus)

    COMPOUNDS['all'] = c

    summary = c.groupby(['categ', 'compound']).apply(lambda d: pd.DataFrame(
        {
            'cas': pd.Series(d.cas.iloc[0]),
            'mass': pd.Series(d.mass.iloc[0]),
            'date': pd.Series(d.date.sort_values(ascending=False).iloc[0]),
            'n_docs': d.is_doc.sum(),
            'n_data': d.is_data.sum(),
            'data_exts': ', '.join(d.loc[d.is_data, 'ext'].unique()),
            'last_user': get_last_user(d),
            'doc_url': d[d.is_doc].iloc[0]['url_view'],
            'doc_mime': d[d.is_doc].iloc[0]['mimeType'],
            'doc_title': d[d.is_doc].iloc[0]['title'],
            'compound_safe': pd.Series(d['compound_safe'].iloc[0]),
        }))
    summary = summary.reset_index()
    summary.drop('level_2', axis=1, inplace=True)

    COMPOUNDS['summary'] = summary
    return COMPOUNDS


def get_categ_tables():
    summary = COMPOUNDS['summary']
    categories = sorted(list(summary.categ.unique()))
    categ_tables = dict()
    for categ in categories:
        categ_tables[categ] = summary[summary.categ == categ]\
            .drop('categ', axis=1)
    return categories, categ_tables


def reload_listing():
    from flask import current_app
    compounds_dir = current_app.config['COMPOUNDS_DIR_ID']
    pickle_path = current_app.config['COMPOUNDS_PICKLE']
    reload_listing_async(compounds_dir, pickle_path)


@asynch
def reload_listing_async(compounds_dir, pickle_path):
    df = file_tree_to_df(compounds_dir, 'compounds')
    df.to_pickle(pickle_path)
    load_prebuilt_listing()
    logger.info('Saved new pickle file.')


load_prebuilt_listing()

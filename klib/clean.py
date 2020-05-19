'''
Functions for data cleaning.

:author: Andreas Kanz

'''

# Imports
import itertools
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from .describe import corr_mat
from .utils import (_diff_report,
                    _drop_duplicates,
                    _missing_vals,
                    _validate_input_bool,
                    _validate_input_range)


__all__ = ['convert_datatypes',
           'data_cleaning',
           'drop_missing',
           'mv_col_handling']


def optimize_ints(data):
    data = pd.DataFrame(data).copy()
    ints = data.select_dtypes(include=['int64']).columns.tolist()
    data[ints] = data[ints].apply(pd.to_numeric, downcast='integer')
    return data


def optimize_floats(data):
    data = pd.DataFrame(data).copy()
    floats = data.select_dtypes(include=['float64']).columns.tolist()
    data[floats] = data[floats].apply(pd.to_numeric, downcast='float')
    return data


def convert_datatypes(data, category=True, cat_threshold=0.05, cat_exclude=None):
    '''
    Converts columns to best possible dtypes using dtypes supporting pd.NA. Temporarily not converting to integers \
        due to an issue in pandas. This is expected to be fixed in pandas 1.1. \
        See https://github.com/pandas-dev/pandas/issues/33803

    Parameters
    ----------
    data: 2D dataset that can be coerced into Pandas DataFrame.

    category: bool, default True
        Change dtypes of columns with dtype "object" to "category". Set threshold using cat_threshold or exclude \
        columns using cat_exclude.

    cat_threshold: float, default 0.05
        Ratio of unique values below which categories are inferred and column dtype is changed to categorical.

    cat_exclude: list, default None
        List of columns to exclude from categorical conversion.

    Returns
    -------
    data: Pandas DataFrame
    '''

    # Validate Inputs
    _validate_input_bool(category, 'Category')
    _validate_input_range(cat_threshold, 'cat_threshold', 0, 1)

    cat_exclude = [] if cat_exclude is None else cat_exclude.copy()

    data = pd.DataFrame(data).copy()
    for col in data.columns:
        unique_vals_ratio = data[col].nunique(dropna=False) / data.shape[0]
        if (category and
            unique_vals_ratio < cat_threshold and
            col not in cat_exclude and
                data[col].dtype == 'object'):
            data[col] = data[col].astype('category')
        data[col] = data[col].convert_dtypes(infer_objects=True, convert_string=True,
                                             convert_integer=False, convert_boolean=True)

    data = optimize_ints(data)
    data = optimize_floats(data)

    return data


def drop_missing(data, drop_threshold_cols=1, drop_threshold_rows=1):
    '''
    Drops completely empty columns and rows by default and optionally provides flexibility to loosen restrictions to \
    drop additional columns and rows based on the fraction of remaining NA-values.

    Parameters
    ----------
    data: 2D dataset that can be coerced into Pandas DataFrame.

    drop_threshold_cols: float, default 1
        Drop columns with NA-ratio above the specified threshold.

    drop_threshold_rows: float, default 1
        Drop rows with NA-ratio above the specified threshold.

    Returns
    -------
    data_cleaned: Pandas DataFrame

    Notes
    -----
    Columns are dropped first. Rows are dropped based on the remaining data.
    '''

    # Validate Inputs
    _validate_input_range(drop_threshold_cols, 'drop_threshold_cols', 0, 1)
    _validate_input_range(drop_threshold_rows, 'drop_threshold_rows', 0, 1)

    data = pd.DataFrame(data).copy()
    data = data.dropna(axis=0, how='all').dropna(axis=1, how='all')
    data = data.drop(columns=data.loc[:, _missing_vals(data)['mv_cols_ratio'] > drop_threshold_cols].columns)
    data_cleaned = data.drop(index=data.loc[_missing_vals(data)['mv_rows_ratio'] > drop_threshold_rows, :].index)

    return data_cleaned


def data_cleaning(data, drop_threshold_cols=0.9, drop_threshold_rows=0.9, drop_duplicates=True,
                  convert_dtypes=True, category=True, cat_threshold=0.03, cat_exclude=None, show='changes'):
    '''
    Perform initial data cleaning tasks on a dataset, such as dropping single valued and empty rows, empty \
        columns as well as optimizing the datatypes.

    Parameters
    ----------
    data: 2D dataset that can be coerced into Pandas DataFrame.

    drop_threshold_cols: float, default 0.9
        Drop columns with NA-ratio above the specified threshold.

    drop_threshold_rows: float, default 0.9
        Drop rows with NA-ratio above the specified threshold.

    drop_duplicates: bool, default True
        Drop duplicate rows, keeping the first occurence. This step comes after the dropping of missing values.

    convert_dtypes: bool, default True
        Convert dtypes using pd.convert_dtypes().

    category: bool, default True
        Enable changing dtypes of 'object' columns to "category". Set threshold using cat_threshold. Requires \
        convert_dtypes=True.

    cat_threshold: float, default 0.03
        Ratio of unique values below which categories are inferred and column dtype is changed to categorical.

    cat_exclude: list, default None
        List of columns to exclude from categorical conversion.

    show: {'all', 'changes', None} default 'all'
        Specify verbosity of the output.
        * 'all': Print information about the data before and after cleaning as well as information about changes.
        * 'changes': Print out differences in the data before and after cleaning.
        * None: No information about the data and the data cleaning is printed.

    Returns
    -------
    data_cleaned: Pandas DataFrame

    See Also
    --------
    convert_datatypes: Convert columns to best possible dtypes.
    drop_missing : Flexibly drop columns and rows.
    _memory_usage: Gives the total memory usage in kilobytes.
    _missing_vals: Metrics about missing values in the dataset.

    Notes
    -----
    The category dtype is not grouped in the summary, unless it contains exactly the same categories.
    '''

    # Validate Inputs
    _validate_input_range(drop_threshold_cols, 'drop_threshold_cols', 0, 1)
    _validate_input_range(drop_threshold_rows, 'drop_threshold_rows', 0, 1)
    _validate_input_bool(drop_duplicates, 'drop_duplicates')
    _validate_input_bool(convert_dtypes, 'convert_datatypes')
    _validate_input_bool(category, 'category')
    _validate_input_range(cat_threshold, 'cat_threshold', 0, 1)

    data = pd.DataFrame(data).copy()
    data_cleaned = drop_missing(data, drop_threshold_cols, drop_threshold_rows)

    single_val_cols = data_cleaned.columns[data_cleaned.nunique(dropna=False) == 1].tolist()
    data_cleaned = data_cleaned.drop(columns=single_val_cols)

    dupl_rows = None

    if drop_duplicates:
        data_cleaned, dupl_rows = _drop_duplicates(data_cleaned)
    if convert_dtypes:
        data_cleaned = convert_datatypes(data_cleaned, category=category, cat_threshold=cat_threshold,
                                         cat_exclude=cat_exclude)

    _diff_report(data, data_cleaned, dupl_rows=dupl_rows, single_val_cols=single_val_cols, show=show)

    return data_cleaned


class DataCleaner(BaseEstimator, TransformerMixin):
    '''
    Wrapper for data_cleaning(). Allows data_cleaning() to be put into a pipeline with similar \
    functions (e.g. using MVColHandler() or SubsetPooler()).

    Parameters:
    ---------´
    drop_threshold_cols: float, default 0.9
        Drop columns with NA-ratio above the specified threshold.

    drop_threshold_rows: float, default 0.9
        Drop rows with NA-ratio above the specified threshold.

    drop_duplicates: bool, default True
        Drop duplicate rows, keeping the first occurence. This step comes after the dropping of missing values.

    convert_dtypes: bool, default True
        Convert dtypes using pd.convert_dtypes().

    category: bool, default True
        Change dtypes of columns to "category". Set threshold using cat_threshold. Requires convert_dtypes=True

    cat_threshold: float, default 0.03
        Ratio of unique values below which categories are inferred and column dtype is changed to categorical.

    cat_exclude: list, default None
        List of columns to exclude from categorical conversion.

    show: {'all', 'changes', None} default 'all'
        Specify verbosity of the output.
        * 'all': Print information about the data before and after cleaning as well as information about changes.
        * 'changes': Print out differences in the data before and after cleaning.
        * None: No information about the data and the data cleaning is printed.

    Returns:
    -------
    data_cleaned: Pandas DataFrame
    '''

    def __init__(self, drop_threshold_cols=0.9, drop_threshold_rows=0.9, drop_duplicates=True, convert_dtypes=True,
                 category=True, cat_threshold=0.03, cat_exclude=None, show='changes'):
        self.drop_threshold_cols = drop_threshold_cols
        self.drop_threshold_rows = drop_threshold_rows
        self.drop_duplicates = drop_duplicates
        self.convert_dtypes = convert_dtypes
        self.category = category
        self.cat_threshold = cat_threshold
        self.cat_exclude = cat_exclude
        self.show = show

    def fit(self, data, target=None):
        return self

    def transform(self, data, target=None):
        data_cleaned = data_cleaning(data, drop_threshold_cols=self.drop_threshold_cols,
                                     drop_threshold_rows=self.drop_threshold_rows, drop_duplicates=self.drop_duplicates,
                                     convert_dtypes=self.convert_dtypes, category=self.category, cat_threshold=self.
                                     cat_threshold, cat_exclude=self.cat_exclude, show=self.show)
        return data_cleaned


def mv_col_handling(data, target=None, mv_threshold=0.1, corr_thresh_features=0.5, corr_thresh_target=0.3,
                    return_details=False):
    '''
    Converts columns with a high ratio of missing values into binary features and eventually drops them based on \
    their correlation with other features and the target variable. This function follows a three step process:
    - 1) Identify features with a high ratio of missing values (above 'mv_threshold').
    - 2) Identify high correlations of these features among themselves and with other features in the dataset (above \
         'corr_thresh_features').
    - 3) Features with high ratio of missing values and high correlation among each other are dropped unless \
         they correlate reasonably well with the target variable (above 'corr_thresh_target').

    Note: If no target is provided, the process exits after step two and drops columns identified up to this point.

    Parameters
    ----------
    data: 2D dataset that can be coerced into Pandas DataFrame.

    target: string, list, np.array or pd.Series, default None
        Specify target for correlation. I.e. label column to generate only the correlations between each feature \
        and the label.

    mv_threshold: float, default 0.1
        Value between 0 <= threshold <= 1. Features with a missing-value-ratio larger than mv_threshold are candidates \
        for dropping and undergo further analysis.

    corr_thresh_features: float, default 0.5
        Value between 0 <= threshold <= 1. Maximum correlation a previously identified features (with a high mv-ratio) \
        is allowed to have with another feature. If this threshold is overstepped, the feature undergoes further \
        analysis.

    corr_thresh_target: float, default 0.3
        Value between 0 <= threshold <= 1. Minimum required correlation of a remaining feature (i.e. feature with a \
        high mv-ratio and high correlation to another existing feature) with the target. If this threshold is not met \
        the feature is ultimately dropped.

    return_details: bool, default False
        Provdies flexibility to return intermediary results.

    Returns
    -------
    data: Updated Pandas DataFrame

    optional:
    cols_mv: Columns with missing values included in the analysis
    drop_cols: List of dropped columns
    '''

    # Validate Inputs
    _validate_input_range(mv_threshold, 'mv_threshold', 0, 1)
    _validate_input_range(corr_thresh_features, 'corr_thresh_features', 0, 1)
    _validate_input_range(corr_thresh_target, 'corr_thresh_target', 0, 1)

    data = pd.DataFrame(data).copy()
    data_local = data.copy()
    mv_ratios = _missing_vals(data_local)['mv_cols_ratio']
    cols_mv = mv_ratios[mv_ratios > mv_threshold].index.tolist()
    data_local[cols_mv] = data_local[cols_mv].applymap(lambda x: 1 if not pd.isnull(x) else x).fillna(0)

    high_corr_features = []
    data_temp = data_local.copy()
    for col in cols_mv:
        corrmat = corr_mat(data_temp, colored=False)
        if abs(corrmat[col]).nlargest(2)[1] > corr_thresh_features:
            high_corr_features.append(col)
            data_temp = data_temp.drop(columns=[col])

    drop_cols = []
    if target is None:
        data = data.drop(columns=high_corr_features)
    else:
        corrs = corr_mat(data_local, target=target, colored=False).loc[high_corr_features]
        drop_cols = corrs.loc[abs(corrs.iloc[:, 0]) < corr_thresh_target].index.tolist()
        data = data.drop(columns=drop_cols)

    if return_details:
        return data, cols_mv, drop_cols

    return data


class MVColHandler(BaseEstimator, TransformerMixin):
    '''
    Wrapper for mv_col_handling(). Allows mv_col_handling() to be put into a pipeline with similar \
    functions (e.g. using DataCleaner() or SubsetPooler()).

    Parameters
    ----------
    target: string, list, np.array or pd.Series, default None
        Specify target for correlation. E.g. label column to generate only the correlations between each feature \
        and the label.

    mv_threshold: float, default 0.1
        Value between 0 <= threshold <= 1. Features with a missing-value-ratio larger than mv_threshold are candidates \
        for dropping and undergo further analysis.

    corr_thresh_features: float, default 0.6
        Value between 0 <= threshold <= 1. Maximum correlation a previously identified features with a high mv-ratio is\
         allowed to have with another feature. If this threshold is overstepped, the feature undergoes further analysis.

    corr_thresh_target: float, default 0.3
        Value between 0 <= threshold <= 1. Minimum required correlation of a remaining feature (i.e. feature with a \
        high mv-ratio and high correlation to another existing feature) with the target. If this threshold is not met \
        the feature is ultimately dropped.

    return_details: bool, default True
        Provdies flexibility to return intermediary results.

    Returns
    -------
    data: Updated Pandas DataFrame
    '''

    def __init__(self, target=None, mv_threshold=0.1, corr_thresh_features=0.6, corr_thresh_target=0.3,
                 return_details=True):
        self.target = target
        self.mv_threshold = mv_threshold
        self.corr_thresh_features = corr_thresh_features
        self.corr_thresh_target = corr_thresh_target
        self.return_details = return_details

    def fit(self, data, target=None):
        return self

    def transform(self, data, target=None):
        data, cols_mv, dropped_cols = mv_col_handling(data, target=self.target, mv_threshold=self.mv_threshold,
                                                      corr_thresh_features=self.corr_thresh_features,
                                                      corr_thresh_target=self.corr_thresh_target,
                                                      return_details=self.return_details)

        print(f'\nFeatures with MV-ratio > {self.mv_threshold}: {len(cols_mv)}')
        print('Features dropped:', len(dropped_cols), dropped_cols)

        return data


def pool_duplicate_subsets(data, col_dupl_thresh=0.2, subset_thresh=0.2, min_col_pool=3, exclude=None,
                           return_details=False):
    '''
    Checks for duplicates in subsets of columns and pools them. This can reduce the number of columns in the data \
    without loosing much information. Suitable columns are combined to subsets and tested for duplicates. In case \
    sufficient duplicates can be found, the respective columns are aggregated into a 'pooled_var' column. Identical \
    numbers in the 'pooled_var' column indicate identical information in the respective rows.

    Parameters
    ----------
    data: 2D dataset that can be coerced into Pandas DataFrame.

    col_dupl_thresh: float, default 0.2
        Columns with a ratio of duplicates higher than 'col_dupl_thresh' are considered in the further analysis. \
        Columns with a lower ratio are not considered for pooling.

    subset_thresh: float, default 0.2
        The first subset with a duplicate threshold higher than 'subset_thresh' is chosen and aggregated. If no subset \
        reaches the threshold, the algorithm continues with continuously smaller subsets until 'min_col_pool' is \
        reached.

    min_col_pool: integer, default 3
        Minimum number of columns to pool. The algorithm attempts to combine as many columns as possible to suitable \
        subsets and stops when 'min_col_pool' is reached.

    exclude. list, default None
        List of column names to be excluded from the analysis. These columns are passed through without modification.

    return_details: bool, default False
        Provdies flexibility to return intermediary results.

    Returns:
    -------
    data: pd.DataFrame

    optional:
    subset_cols: List of columns used as subset.
    '''

    # Input validation
    _validate_input_range(col_dupl_thresh, 'col_dupl_thresh', 0, 1)
    _validate_input_range(subset_thresh, 'subset_thresh', 0, 1)
    _validate_input_range(min_col_pool, 'min_col_pool', 0, data.shape[1])

    excluded_cols = []
    if exclude is not None:
        excluded_cols = data[exclude]
        data = data.drop(columns=exclude)

    subset_cols = []
    for i in range(data.shape[1]+1-min_col_pool):
        check_list = [col for col in data.columns if data.duplicated(subset=col).mean() > col_dupl_thresh]

        if len(check_list) > 0:
            combinations = itertools.combinations(check_list, len(check_list)-i)
        else:
            continue

        ratios = [*map(lambda comb: data[list(comb)].duplicated().mean(), combinations)]

        max_ratio = max(ratios)
        max_idx = np.argmax(ratios)

        if max_ratio > subset_thresh:
            best_subset = itertools.islice(itertools.combinations(
                check_list, len(check_list)-i), max_idx, max_idx+1)
            best_subset = data[list(list(best_subset)[0])]
            subset_cols = best_subset.columns.tolist()

            unique_subset = best_subset.drop_duplicates().reset_index().rename(columns={'index': 'pooled_vars'})
            data = data.merge(unique_subset, how='left', on=best_subset.columns.tolist()
                              ).drop(columns=best_subset.columns.tolist())
            data.index = pd.RangeIndex(len(data))
            break

    data = pd.concat([data, pd.DataFrame(excluded_cols)], axis=1)

    if return_details:
        return data, subset_cols

    return data


class SubsetPooler(BaseEstimator, TransformerMixin):
    '''
    Wrapper for pool_duplicate_subsets(). Allows pool_duplicate_subsets() to be put into a pipeline with similar \
    functions (e.g. using DataCleaner() or MVColHandler()).

    Parameters
    ----------
    col_dupl_ratio: float, default 0.2
        Columns with a ratio of duplicates higher than 'col_dupl_ratio' are considered in the further analysis. \
        Columns with a lower ratio are not considered for pooling.

    dupl_thresh: float, default 0.2
        The first subset with a duplicate threshold higher than 'dupl_thresh' is chosen and aggregated. If no subset \
        reaches the threshold, the algorithm continues with continuously smaller subsets until 'min_col_pool' is \
        reached.

    min_col_pool: integer, default 3
        Minimum number of columns to pool. The algorithm attempts to combine as many columns as possible to suitable \
        subsets and stops when 'min_col_pool' is reached.

    return_details: bool, default False
        Provdies flexibility to return intermediary results.

    Returns:
    -------
    data: pd.DataFrame
    '''

    def __init__(self, col_dupl_thresh=0.2, subset_thresh=0.2, min_col_pool=3, return_details=True):
        self.col_dupl_thresh = col_dupl_thresh
        self.subset_thresh = subset_thresh
        self.min_col_pool = min_col_pool
        self.return_details = return_details

    def fit(self, data, target=None):
        return self

    def transform(self, data, target=None):
        data, subset_cols = pool_duplicate_subsets(
            data, col_dupl_thresh=0.2, subset_thresh=0.2, min_col_pool=3, return_details=True)

        print('Combined columns:', len(subset_cols), subset_cols)

        return data

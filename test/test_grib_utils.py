from fdb_utils.grib_utils import extract_metadata_from_grib_file
from test.conftest import data_dir

def test_extract_metadata_from_grib_file(data_dir):

    grib_file = data_dir / 'test.grib'
    
    result = extract_metadata_from_grib_file(grib_file)

    expected = {
        'date': '20260710',
        'time': '0600',
        'step': 1,
        'number': 1,
    }

    assert expected == result

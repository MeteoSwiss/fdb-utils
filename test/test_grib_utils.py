from fdb_utils.grib_utils import extract_metadata_from_grib_file
from test.conftest import data_dir

def test_extract_metadata_from_grib_file(data_dir):

    grib_file = data_dir / 'test.grib'
    
    result = extract_metadata_from_grib_file(grib_file)

    expected = {
        'date': '20230201',
        'time': '0300',
        'step': 7,
        'number': 3,
    }

    assert expected == result

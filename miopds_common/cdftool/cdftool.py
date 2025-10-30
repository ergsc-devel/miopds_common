import cdflib

from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Union



@dataclass
class VARInfo:
    """
    Variable record info.
    """

    #: Name of the variable.
    Variable: str
    #: Variable number.
    Num: int
    #: Variable type: zVariable or rVariable.
    Var_Type: str
    #: Variable CDF data type.
    Data_Type: int
    Data_Type_Description: str
    #: Number of elements of the variable.
    Num_Elements: int
    #: Dimensionality of variable record.
    Num_Dims: int
    #: Shape of the variable record.
    Dim_Sizes: List[int]
    #: Max. record
    Max_Rec: int
    #: File offset
    File_Offset: int



class cdfinfo:
    """
    An experimental version of the CDF tools that are to be used by Mio Science Center 
    to extract some information from a data file in CDF for populating a PDS label.

    Usage:
        import cdftool
        info = cdftool.cdfinfo("bc_mmo_spm_l2p_cnt_20210810_r00-v00-00.cdf")
        info.var_info

    var_info is a dictionary containing the following keys and values:
      var_no  : the serial number of a data array
      data_type:   the variable type in integer
      max_rec  :   the number of records stored in a data array
      offset_for_block: the offset for the data block of a data array
      offset_for_var  : the offset of a data array counting from the top of the CDF file
   
    Please note that this function is applicable only to an uncompressed CDF file 
    containing only Z variables and not including sparse / virtual variables. 
    """

    def __init__(self, path: Union[str, Path]):
        
        if isinstance(path, Path):
            fname = path.absolute().as_posix()
        else:
            fname = path
        
        self.ftype = "file"
        path = Path(path).resolve().expanduser()
        if not path.is_file():
            path = path.with_suffix(".cdf")
            if not path.is_file():
                raise FileNotFoundError(f"{path} not found")
        self.file = path

        cdf = cdflib.CDF(self.file)
        zvars = cdf.cdf_info().zVariables 

        self.var_info = {}
        for zvarnm in zvars:

            vdr = cdf.vdr_info(zvarnm)
            vvr_offsets, vvr_start, vvr_end = cdf._read_vxrs(vdr.head_vxr, vvr_offsets=[], vvr_start=[], vvr_end=[])

            self.var_info[zvarnm] = {
                'var_no':vdr.variable_number,
                'data_type':vdr.data_type,
                'max_rec':vdr.max_rec,
                'offset_for_block':vvr_offsets[0],
                'offset_for_var':vvr_offsets[0] + 8 + 4,   ## block size (8) + section type (4)
            }













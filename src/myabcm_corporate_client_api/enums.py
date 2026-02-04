from enum import IntEnum

# Client API
class AbmFactType(IntEnum):
    None_ = -1
    CrossModule = 0   #Regular In/Out
    SingleModule = 1
    SQL = 2           #Dynamic SQL (not renamed because UI)
    StaticSQL = 3

class LogonResult(IntEnum):
    Ok = 0
    Unknown = 1
    UserUnknown = 2
    WrongPassword = 3
    DatabaseUnknown = 4
    ActiveDirectoryAuthenticationFailed = 5
    PasswordExpired = 6
    ProductNotAuthorized = 7
    NoLicenseAvailable = 8
    UserNotAuthorized = 9
    TokenAuthenticationFailed = 10
    UserOrPasswordUnknown = 11

class AbmDataSourceType(IntEnum):
    """Data source types"""
    Excel = 0,
    Access = 1,
    OLEDB = 2,
    SQLServer = 3,
    Oracle = 4,
    ETL = 5,
    Internal = 6,
    DataMap = 7,
    SharedFile = 8

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_

class AbmOperationType(IntEnum):
    """Operation types"""
    Calcule = 0
    CubeGeneration = 1
    Import = 2
    ScenarioBuild = 3
    MemberExclusion = 4
    Export = 5
    SurveysUpload = 6
    RemoveModel = 8
    FactGeneration = 9
    RemoveFactAssociation = 10
    RemoveCube = 11
    RemoveCubesFromOLAPServer = 12
    ImportUsers = 13
    ImportUserGroups = 14
    EtlPackage = 15
    CalculateKPI = 16
    SendKPIAlert = 17

class AbmOperationStatus(IntEnum):
    None_ = -1
    Scheduled = 0
    InProgress = 1
    Aborting = 2
    Finished = 3
    Aborted = 4
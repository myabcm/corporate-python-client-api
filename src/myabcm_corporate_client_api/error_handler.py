import json
from enum import IntEnum

class ExceptionCodes(IntEnum):
    """Exception codes matching the TypeScript ExceptionCodes enum."""
    Null = 0
    Unknown = 1
    UserUnknown = 2
    WrongPassword = 3
    MyABCMServerNotFound = 4
    MyABCMServerFaultedState = 5
    SendEmailFailed = 6
    EmailNotFound = 7
    ActiveDirectoryAuthenticationFailed = 8
    PasswordExpired = 9
    InvalidOperationToExternalUser = 10
    DatabaseUnknown = 11
    InvalidDatabaseName = 12
    InvalidHostName = 13
    InvalidHostOrDatabaseName = 14
    DatabaseLoginFailed = 15
    ReportingObjectReceiveFailure = 16
    DatabaseAlreadyExists = 17
    ReportingNotFound = 18
    InvalidSiteSessionTimeout = 19
    InvalidUserTable = 20
    InvalidMaxLengthField = 21
    InvalidSessionToken = 22
    UserExistsInSurveys = 23
    PreviewExportFailed = 24
    FullModelExportFailed = 25
    AliasRequirementCheckFailed = 26
    FileAlreadyExists = 27
    FileNotFound = 28
    PreviewReportingFailed = 29
    FileIsBeingUsedByAnotherProcess = 30
    ExportNotFound = 31
    ImportNotFound = 32
    ScriptNotFound = 33
    FactNotFound = 34
    CubeNotFound = 35
    GetCubeViewConnectionStringFailed = 36

    DuplicatedReference = 37
    CannotInsertNull = 38
    ColumnWasSpecifiedMultipleTimesForTable = 39
    GenericDbException = 40
    PreviewQueryException = 41

    LicenseExpiredException = 42
    GetLicenseException = 43
    AddLicenseException = 44
    PreviewFactFailed = 45

    InvalidCultureCode = 46

    FactAssociationNotFound = 47

    MethodNotSupported = 48

    InvalidCube = 49

    RangeNotFoundInSurveyTemplate = 50
    TemplateFileNotFound = 51
    UpdateSurveyDataFailed = 52

    InvalidStrongPassword = 53

    SerializationFailed = 54
    DeserializationFailed = 55
    DimensionDoesNotExistInDatabase = 56
    TextAttributeDoesNotExistInDatabase = 57
    PredefinedMeasureDoesNotExistInDatabase = 58
    NumericAttributeDoesNotExistInDatabase = 59
    FactDoesNotExistInDatabase = 60
    ModuleDoesNotExistInDatabase = 61
    CommonMeasureDoesNotExistInDatabase = 62
    CubeDoesNotContainOlapXml = 63
    XmlManuallyModified = 64
    UnsupportedXmlVersion = 65
    ModuleDoesNotExistInModel = 66
    InvalidSourceModule = 67
    DuplicatedFact = 68
    DuplicatedFactDestination = 69
    InconsistentFactSelection = 70
    NoMeasureSelected = 71

    KPISourceTypeNotDefined = 72

    CubeTypeMismatchOrInvalidContent = 73

    PermissionToDatabaseDenied = 74

    TokenAuthenticationFailed = 75

    ExportTemplateImportIsDisabled = 76

    TransferFileOwnershipInterrupted = 77

    RenameFileFailed = 78

    CommunicationError = 79

    UserPrivateSpaceHasBeenExceeded = 80

    UploadMaxFileSizeHasBeenExceeded = 81

    RemoveModuleDimensionFailed = 50001
    RemoveAssignmentsFailed = 50002
    AddPeriodScenarioFailed = 50003
    AddMemberInParentDifferentModule = 50004
    AddDimMemberInParentDifferentDimension = 50005
    AddMemberDimensionFailed = 50006
    AddMemberInstanceInParentDifferentModelPeriodScenario = 50007
    AddAssignmentsFailed = 50008

    UpdateMemberInDifferenteModuleParentFailed = 50020,
    UpdateParentMemberFailed = 50021,
    UpdateDimensionMemberInParentDifferentDimensionFailed = 50024,
    UpdateMemberDimensionFailed = 50026,
    AddMemberFailed = 50051,
    AddAssignmentsCostBackFailed = 50052,
    UpdateModuleOrderFailed = 50053,
    AddAttributeFailed = 50054,
    AddAttributeInstancesFailed = 50055,

    FixedDriverAlreadyDefined = 50064,
    RemoveMemberIsInUse = 50065,
    RemovePeriodIsInUse = 50066,
    RemoveScenarioIsInUse = 50067,
    RemoveAttributeIsInUse = 50068,
    RemoveDriverIsInUse = 50069,
    ModelAccessRightValidationFailed = 50070,
    AssociationAccessRightValidationFailed = 50071,
    StruturalMemberAccessRightValidationFailed = 50072,
    MemberInstanceAccessRightValidationFailed = 50073,
    FileAccessRightValidationFailed = 50074,
    AnalysisObjectGroupAccessRightValidationFailed = 50075,
    ReportAccessRightValidationFailed = 50076,
    IntegrationAccessRightValidationFailed = 50077,
    AnalysisAccessRightValidationFailed = 50078,
    AttributeReferenceInvalid = 50079,

    RemoveFactsFailed = 50082,
    CubeViewAccessRightValidationFailed = 50083,

    UpdateAssignmentWhenIsFixedFailed = 50093,
    DeleteAttributeInstanceFailed = 50094,
    UpdateAttributeWhenExistsFixed = 50095,
    UpdateDriverWhenExistsFixed = 50098,
    AddInvalidDriverToMemberInstance = 50099,

    CannotExistsMoreThanOneLocalizationInfo = 50106,
    AddMemberDimensionFailed2 = 50107,
    UpdateMemberDimensionFailed2 = 50108,
    DashboardAccessRightValidationFailed = 50111,
    RemoveExportTemplateIsInUse = 50112,
    DiagramAccessRightValidationFailed = 50113,

    PasswordDoesNotMeetHistoryRequirements = 50119,
    KPIGroupAccessRightValidationFailed = 50120,
    KPIAccessRightValidationFailed = 50121,
    RemoveKPIGroupIsInUse = 50122,
    RemoveKPIIsInUse = 50123,
    CannotUpdateGoalIfSourceIsEmptyTotalingFunction = 50135,
    CubeAccessRightValidationFailed = 50138,
    AddCubeFactWithDifferentFactType = 50141,
    AddMoreThanOneSQLFactInCubeFact = 50142,
    TabularCubesOnlySupportSQLStaticFacts = 50143,

class CustomError(Exception):
    """Custom error class that matches the TypeScript CustomError structure."""
    def __init__(self, error_code, message):
        self.error_code = int(error_code)
        self.message = message
        super().__init__(message)

# Message mapping dictionary
EXCEPTION_CODE_TO_MESSAGE = {
    ExceptionCodes.Unknown: 'Unknown error occurred',
    ExceptionCodes.MethodNotSupported: 'Method not supported',
    ExceptionCodes.MyABCMServerNotFound: 'MyABCM server not found',
    ExceptionCodes.CommunicationError: 'Communication error',
    ExceptionCodes.InvalidSessionToken: 'Invalid session token',
    ExceptionCodes.MyABCMServerFaultedState: 'MyABCM server is in faulted state',
    ExceptionCodes.GenericDbException: 'Generic database exception',
    ExceptionCodes.EmailNotFound: 'Email not found',
    ExceptionCodes.InvalidStrongPassword: 'Invalid strong password',
    ExceptionCodes.SendEmailFailed: 'Send email failed',
    ExceptionCodes.UserUnknown: 'User unknown',
    ExceptionCodes.InvalidOperationToExternalUser: 'Invalid operation to external user',
    ExceptionCodes.InvalidMaxLengthField: 'Invalid max length field',
    ExceptionCodes.FileIsBeingUsedByAnotherProcess: 'File is being used by another process',
    ExceptionCodes.FileNotFound: 'File not found',
    ExceptionCodes.DuplicatedReference: 'Duplicated reference',
    ExceptionCodes.AddPeriodScenarioFailed: 'Add period scenario failed',
    ExceptionCodes.RemoveAssignmentsFailed: 'Remove assignments failed',
    ExceptionCodes.AddMemberDimensionFailed: 'Add member dimension failed',
    ExceptionCodes.RemoveModuleDimensionFailed: 'Remove module dimension failed',
    ExceptionCodes.AddMemberInParentDifferentModule: 'Add member in parent different module',
    ExceptionCodes.AddDimMemberInParentDifferentDimension: 'Add dimension member in parent different dimension',
    ExceptionCodes.AddMemberInstanceInParentDifferentModelPeriodScenario: 'Add member instance in parent different model period scenario',
    ExceptionCodes.AddAssignmentsFailed: 'Add assignments failed',
    ExceptionCodes.PreviewQueryException: 'Preview query exception',
    ExceptionCodes.PreviewExportFailed: 'Preview export failed',
    ExceptionCodes.PreviewFactFailed: 'Preview fact failed',
    ExceptionCodes.ColumnWasSpecifiedMultipleTimesForTable: 'Column was specified multiple times for table',
    ExceptionCodes.PermissionToDatabaseDenied: 'Permission to database denied',
    ExceptionCodes.ExportNotFound: 'Export not found',
    ExceptionCodes.AliasRequirementCheckFailed: 'Alias requirement check failed',
    ExceptionCodes.FileAlreadyExists: 'File already exists',
    ExceptionCodes.ImportNotFound: 'Import not found',
    ExceptionCodes.ScriptNotFound: 'Script not found',
    ExceptionCodes.PreviewReportingFailed: 'Preview reporting failed',
    ExceptionCodes.InvalidCube: 'Invalid cube',
    ExceptionCodes.FactNotFound: 'Fact not found',
    ExceptionCodes.FactAssociationNotFound: 'Fact association not found',
    ExceptionCodes.CubeNotFound: 'Cube not found',
    ExceptionCodes.SerializationFailed: 'Serialization failed',
    ExceptionCodes.DeserializationFailed: 'Deserialization failed',
    ExceptionCodes.DimensionDoesNotExistInDatabase: 'Dimension does not exist in database',
    ExceptionCodes.TextAttributeDoesNotExistInDatabase: 'Text attribute does not exist in database',
    ExceptionCodes.PredefinedMeasureDoesNotExistInDatabase: 'Predefined measure does not exist in database',
    ExceptionCodes.NumericAttributeDoesNotExistInDatabase: 'Numeric attribute does not exist in database',
    ExceptionCodes.FactDoesNotExistInDatabase: 'Fact does not exist in database',
    ExceptionCodes.ModuleDoesNotExistInDatabase: 'Module does not exist in database',
    ExceptionCodes.CommonMeasureDoesNotExistInDatabase: 'Common measure does not exist in database',
    ExceptionCodes.CubeDoesNotContainOlapXml: 'Cube does not contain OLAP XML',
    ExceptionCodes.XmlManuallyModified: 'XML manually modified',
    ExceptionCodes.UnsupportedXmlVersion: 'Unsupported XML version',
    ExceptionCodes.ModuleDoesNotExistInModel: 'Module does not exist in model',
    ExceptionCodes.InvalidSourceModule: 'Invalid source module',
    ExceptionCodes.DuplicatedFact: 'Duplicated fact',
    ExceptionCodes.DuplicatedFactDestination: 'Duplicated fact destination',
    ExceptionCodes.InconsistentFactSelection: 'Inconsistent fact selection',
    ExceptionCodes.NoMeasureSelected: 'No measure selected',
    ExceptionCodes.KPISourceTypeNotDefined: 'KPI source type not defined',
    ExceptionCodes.CubeTypeMismatchOrInvalidContent: 'Cube type mismatch or invalid content',
    ExceptionCodes.RenameFileFailed: 'Rename file failed',
    ExceptionCodes.UploadMaxFileSizeHasBeenExceeded: 'Upload max file size has been exceeded',
    ExceptionCodes.UpdateMemberInDifferenteModuleParentFailed: 'Update member in different module parent failed',
    ExceptionCodes.UpdateParentMemberFailed: 'Update parent member failed',
    ExceptionCodes.UpdateDimensionMemberInParentDifferentDimensionFailed: 'Update dimension member in parent different dimension failed',
    ExceptionCodes.UpdateMemberDimensionFailed: 'Update member dimension failed',
    ExceptionCodes.AddMemberFailed: 'Add member failed',
    ExceptionCodes.AddAssignmentsCostBackFailed: 'Add assignments cost back failed',
    ExceptionCodes.UpdateModuleOrderFailed: 'Update module order failed',
    ExceptionCodes.AddAttributeFailed: 'Add attribute failed',
    ExceptionCodes.AddAttributeInstancesFailed: 'Add attribute instances failed',
    ExceptionCodes.FixedDriverAlreadyDefined: 'Fixed driver already defined',
    ExceptionCodes.RemoveMemberIsInUse: 'Remove member is in use',
    ExceptionCodes.RemovePeriodIsInUse: 'Remove period is in use',
    ExceptionCodes.RemoveScenarioIsInUse: 'Remove scenario is in use',
    ExceptionCodes.RemoveAttributeIsInUse: 'Remove attribute is in use',
    ExceptionCodes.RemoveDriverIsInUse: 'Remove driver is in use',
    ExceptionCodes.ModelAccessRightValidationFailed: 'Model access right validation failed',
    ExceptionCodes.AssociationAccessRightValidationFailed: 'Association access right validation failed',
    ExceptionCodes.StruturalMemberAccessRightValidationFailed: 'Strutural member access right validation failed',
    ExceptionCodes.MemberInstanceAccessRightValidationFailed: 'Member instance access right validation failed',
    ExceptionCodes.FileAccessRightValidationFailed: 'File access right validation failed',
    ExceptionCodes.AnalysisObjectGroupAccessRightValidationFailed: 'Analysis object group access right validation failed',
    ExceptionCodes.ReportAccessRightValidationFailed: 'Report access right validation failed',
    ExceptionCodes.IntegrationAccessRightValidationFailed: 'Integration access right validation failed',
    ExceptionCodes.AnalysisAccessRightValidationFailed: 'Analysis access right validation failed',
    ExceptionCodes.AttributeReferenceInvalid: 'Attribute reference invalid',
    ExceptionCodes.RemoveFactsFailed: 'Remove facts failed',
    ExceptionCodes.CubeViewAccessRightValidationFailed: 'Cube view access right validation failed',
    ExceptionCodes.UpdateAssignmentWhenIsFixedFailed: 'Update assignment when is fixed failed',
    ExceptionCodes.DeleteAttributeInstanceFailed: 'Delete attribute instance failed',
    ExceptionCodes.UpdateAttributeWhenExistsFixed: 'Update attribute when exists fixed',
    ExceptionCodes.UpdateDriverWhenExistsFixed: 'Update driver when exists fixed',
    ExceptionCodes.AddInvalidDriverToMemberInstance: 'Add invalid driver to member instance',
    ExceptionCodes.CannotExistsMoreThanOneLocalizationInfo: 'Cannot exists more than one localization info',
    ExceptionCodes.AddMemberDimensionFailed2: 'Add member dimension failed 2',
    ExceptionCodes.UpdateMemberDimensionFailed2: 'Update member dimension failed 2',
    ExceptionCodes.DashboardAccessRightValidationFailed: 'Dashboard access right validation failed',
    ExceptionCodes.RemoveExportTemplateIsInUse: 'Remove export template is in use',
    ExceptionCodes.DiagramAccessRightValidationFailed: 'Diagram access right validation failed',
    ExceptionCodes.PasswordDoesNotMeetHistoryRequirements: 'Password does not meet history requirements',
    ExceptionCodes.KPIGroupAccessRightValidationFailed: 'KPI group access right validation failed',
    ExceptionCodes.KPIAccessRightValidationFailed: 'KPI access right validation failed',
    ExceptionCodes.RemoveKPIGroupIsInUse: 'Remove KPI group is in use',
    ExceptionCodes.RemoveKPIIsInUse: 'Remove KPI is in use',
    ExceptionCodes.CannotUpdateGoalIfSourceIsEmptyTotalingFunction: 'Cannot update goal if source is empty totaling function',
    ExceptionCodes.CubeAccessRightValidationFailed: 'Cube access right validation failed',
    ExceptionCodes.AddCubeFactWithDifferentFactType: 'Add cube fact with different fact type',
    ExceptionCodes.AddMoreThanOneSQLFactInCubeFact: 'Add more than one SQL fact in cube fact',
    ExceptionCodes.TabularCubesOnlySupportSQLStaticFacts: 'Tabular cubes only support SQL static facts',

}

def get_error_message_from_response(response_content):
    """
    Extracts the error from JSON and returns the user-friendly MESSAGE.
    """
    try:
        if not response_content:
            return "Empty response"

        data = json.loads(response_content.decode('utf-8'))
        error_code = data.get('ErrorCode')

        if error_code is not None:
            return EXCEPTION_CODE_TO_MESSAGE.get(error_code, "Unknown error")

        return "Unknown error (ErrorCode is missing)"

    except json.JSONDecodeError:
        return response_content.decode('utf-8')

    except Exception as e:
        return f"Error parsing response: {str(e)}"
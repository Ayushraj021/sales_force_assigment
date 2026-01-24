# Backend GraphQL API Requirements

This document lists all GraphQL APIs that need to be created in the backend to support the frontend UI components.

## Current Backend APIs (Already Implemented)

### Queries (10 total)
| Query | Parameters | Return Type | Status |
|-------|------------|-------------|--------|
| `me` | None | `UserType` | ✅ Exists |
| `user` | `id: UUID` | `UserType` | ✅ Exists |
| `users` | `limit: Int, offset: Int` | `[UserType]` | ✅ Exists |
| `organization` | `id: UUID?` | `OrganizationType` | ✅ Exists |
| `model` | `id: UUID` | `ModelType` | ✅ Exists |
| `models` | `modelType: String?, status: String?, limit: Int, offset: Int` | `[ModelType]` | ✅ Exists |
| `experiment` | `id: UUID` | `ExperimentType` | ✅ Exists |
| `experiments` | `status: String?, limit: Int, offset: Int` | `[ExperimentType]` | ✅ Exists |
| `health` | None | `String` | ✅ Exists |
| `version` | None | `String` | ✅ Exists |

### Mutations (7 total)
| Mutation | Input Type | Return Type | Status |
|----------|------------|-------------|--------|
| `register` | `RegisterInput` | `AuthPayload` | ✅ Exists |
| `login` | `LoginInput` | `AuthPayload` | ✅ Exists |
| `refreshToken` | `refresh_token: String` | `TokenType` | ✅ Exists |
| `updateProfile` | `UpdateUserInput` | `UserType` | ✅ Exists |
| `changePassword` | `ChangePasswordInput` | `Boolean` | ✅ Exists |
| `predict` | `PredictInput` | `PredictionResult` | ✅ Exists |
| `decomposeContributions` | `DecomposeInput` | `DecompositionResult` | ✅ Exists |

---

## APIs Required for Frontend Components

### 1. User Management (UserManagement.tsx)

**Required Mutations:**

```graphql
# Invite a new user to the organization
mutation createUser($input: CreateUserInput!) {
  createUser(input: $input) {
    id
    email
    firstName
    lastName
    isActive
    roles { id name }
    createdAt
  }
}

input CreateUserInput {
  email: String!
  firstName: String
  lastName: String
  roleId: UUID
  sendInvite: Boolean = true
}
```

```graphql
# Update an existing user
mutation updateUser($id: UUID!, $input: UpdateUserInput!) {
  updateUser(id: $id, input: $input) {
    id
    email
    firstName
    lastName
    isActive
    roles { id name }
    updatedAt
  }
}

input UpdateUserInput {
  firstName: String
  lastName: String
  roleId: UUID
  isActive: Boolean
}
```

```graphql
# Delete/deactivate a user
mutation deleteUser($id: UUID!) {
  deleteUser(id: $id)
}
```

---

### 2. Organization Settings (OrganizationSettings.tsx)

**Required Mutations:**

```graphql
# Update organization settings
mutation updateOrganization($id: UUID!, $input: UpdateOrganizationInput!) {
  updateOrganization(id: $id, input: $input) {
    id
    name
    slug
    description
    settings
    updatedAt
  }
}

input UpdateOrganizationInput {
  name: String
  slug: String
  description: String
  settings: JSON  # For industry, timezone, currency, fiscalYearStart, etc.
}
```

---

### 3. Password Reset (ForgotPasswordForm.tsx, ResetPasswordForm.tsx)

**Required Mutations:**

```graphql
# Request password reset email
mutation forgotPassword($email: String!) {
  forgotPassword(email: $email)
}
```

```graphql
# Reset password with token
mutation resetPassword($input: ResetPasswordInput!) {
  resetPassword(input: $input) {
    success
    message
  }
}

input ResetPasswordInput {
  token: String!
  newPassword: String!
}
```

```graphql
# Verify email (for registration flow)
mutation verifyEmail($token: String!) {
  verifyEmail(token: $token) {
    success
    message
  }
}
```

---

### 4. Dataset Management (DataUpload.tsx, DataSourceList.tsx)

**Required Queries:**

```graphql
# List all datasets
query datasets($limit: Int, $offset: Int) {
  datasets(limit: $limit, offset: $offset) {
    id
    name
    description
    fileName
    fileSize
    rowCount
    columnCount
    columns
    schema
    status
    createdAt
    updatedAt
  }
}

# Get single dataset details
query dataset($id: UUID!) {
  dataset(id: $id) {
    id
    name
    description
    fileName
    fileSize
    rowCount
    columnCount
    columns
    schema
    preview  # First 10 rows as JSON
    statistics  # Column statistics
    status
    createdAt
    updatedAt
  }
}
```

**Required Mutations:**

```graphql
# Create dataset from uploaded file
mutation createDataset($input: CreateDatasetInput!) {
  createDataset(input: $input) {
    id
    name
    status
    columns
    rowCount
  }
}

input CreateDatasetInput {
  name: String!
  description: String
  fileKey: String!  # S3 key or temporary file reference
  dateColumn: String
  targetColumn: String
  channelColumns: [String!]
}
```

```graphql
# Update dataset metadata
mutation updateDataset($id: UUID!, $input: UpdateDatasetInput!) {
  updateDataset(id: $id, input: $input) {
    id
    name
    description
    updatedAt
  }
}

input UpdateDatasetInput {
  name: String
  description: String
  dateColumn: String
  targetColumn: String
  channelColumns: [String!]
}
```

```graphql
# Delete dataset
mutation deleteDataset($id: UUID!) {
  deleteDataset(id: $id)
}
```

---

### 5. Data Connectors (DataConnectors.tsx)

**Required Types:**

```graphql
type DataConnector {
  id: UUID!
  name: String!
  connectorType: String!  # bigquery, snowflake, google-ads, etc.
  status: String!  # connected, disconnected, error
  lastSyncAt: DateTime
  config: JSON  # Non-sensitive config
  createdAt: DateTime!
  updatedAt: DateTime!
}
```

**Required Queries:**

```graphql
# List all data connectors
query dataConnectors {
  dataConnectors {
    id
    name
    connectorType
    status
    lastSyncAt
    createdAt
  }
}

# Get connector details
query dataConnector($id: UUID!) {
  dataConnector(id: $id) {
    id
    name
    connectorType
    status
    config
    lastSyncAt
    syncHistory {
      id
      status
      recordsProcessed
      startedAt
      completedAt
      error
    }
  }
}
```

**Required Mutations:**

```graphql
# Create a new data connector
mutation createDataConnector($input: CreateDataConnectorInput!) {
  createDataConnector(input: $input) {
    id
    name
    connectorType
    status
  }
}

input CreateDataConnectorInput {
  name: String!
  connectorType: String!
  credentials: JSON!  # Encrypted credentials
  config: JSON  # Additional configuration
}
```

```graphql
# Test connector credentials
mutation testDataConnector($input: TestDataConnectorInput!) {
  testDataConnector(input: $input) {
    success
    message
    tables: [String!]  # Available tables if successful
  }
}

input TestDataConnectorInput {
  connectorType: String!
  credentials: JSON!
}
```

```graphql
# Update connector
mutation updateDataConnector($id: UUID!, $input: UpdateDataConnectorInput!) {
  updateDataConnector(id: $id, input: $input) {
    id
    name
    status
    updatedAt
  }
}

input UpdateDataConnectorInput {
  name: String
  credentials: JSON
  config: JSON
}
```

```graphql
# Delete connector
mutation deleteDataConnector($id: UUID!) {
  deleteDataConnector(id: $id)
}
```

```graphql
# Trigger manual sync
mutation syncDataConnector($id: UUID!) {
  syncDataConnector(id: $id) {
    id
    status
    message
  }
}
```

---

### 6. Model Management (ModelCreationWizard.tsx, ModelList.tsx, ModelDetail.tsx)

**Required Mutations:**

```graphql
# Create a new model
mutation createModel($input: CreateModelInput!) {
  createModel(input: $input) {
    id
    name
    modelType
    status
    createdAt
  }
}

input CreateModelInput {
  name: String!
  description: String
  modelType: String!  # mmm, attribution, forecast, causal
  datasetId: UUID!
  targetColumn: String!
  dateColumn: String!
  channelColumns: [String!]!
  config: JSON  # Model-specific configuration
  hyperparameters: JSON
}
```

```graphql
# Update model
mutation updateModel($id: UUID!, $input: UpdateModelInput!) {
  updateModel(id: $id, input: $input) {
    id
    name
    description
    updatedAt
  }
}

input UpdateModelInput {
  name: String
  description: String
  config: JSON
  hyperparameters: JSON
}
```

```graphql
# Delete model
mutation deleteModel($id: UUID!) {
  deleteModel(id: $id)
}
```

```graphql
# Start model training
mutation trainModel($id: UUID!, $input: TrainModelInput) {
  trainModel(id: $id, input: $input) {
    id
    status
    trainingJobId
    estimatedDuration
  }
}

input TrainModelInput {
  adstockConfig: AdstockConfigInput
  saturationConfig: SaturationConfigInput
  mcmcSamples: Int
  mcmcChains: Int
  trainTestSplit: Float
}

input AdstockConfigInput {
  channelName: String!
  adstockType: String!  # geometric, weibull
  maxLag: Int!
  decayRate: Float
  normalize: Boolean
}

input SaturationConfigInput {
  channelName: String!
  saturationType: String!  # hill, logistic, michaelis_menten
  alpha: Float
  gamma: Float
}
```

```graphql
# Cancel model training
mutation cancelTraining($id: UUID!) {
  cancelTraining(id: $id)
}
```

```graphql
# Promote model version
mutation promoteModelVersion($modelId: UUID!, $versionId: UUID!) {
  promoteModelVersion(modelId: $modelId, versionId: $versionId) {
    id
    version
    isCurrent
  }
}
```

---

### 7. Forecast Management (ForecastGeneration.tsx)

**Required Types:**

```graphql
type Forecast {
  id: UUID!
  name: String!
  modelId: UUID!
  model: ModelType!
  horizon: Int!
  granularity: String!
  predictions: JSON!
  confidenceIntervals: JSON
  metrics: JSON
  createdAt: DateTime!
  createdBy: UserType!
}
```

**Required Queries:**

```graphql
# List forecasts
query forecasts($modelId: UUID, $limit: Int, $offset: Int) {
  forecasts(modelId: $modelId, limit: $limit, offset: $offset) {
    id
    name
    modelId
    model { name modelType }
    horizon
    granularity
    createdAt
    createdBy { fullName }
  }
}

# Get forecast details
query forecast($id: UUID!) {
  forecast(id: $id) {
    id
    name
    modelId
    horizon
    granularity
    predictions
    confidenceIntervals
    metrics
    createdAt
  }
}
```

**Required Mutations:**

```graphql
# Save a forecast
mutation saveForecast($input: SaveForecastInput!) {
  saveForecast(input: $input) {
    id
    name
    createdAt
  }
}

input SaveForecastInput {
  name: String!
  modelId: UUID!
  horizon: Int!
  granularity: String!
  predictions: JSON!
  confidenceIntervals: JSON
  metrics: JSON
}
```

```graphql
# Delete forecast
mutation deleteForecast($id: UUID!) {
  deleteForecast(id: $id)
}
```

---

### 8. Report Management (ReportBuilder.tsx)

**Required Types:**

```graphql
type Report {
  id: UUID!
  name: String!
  templateType: String!
  sections: [String!]!
  config: JSON
  status: String!  # draft, generating, completed, failed
  fileUrl: String
  createdAt: DateTime!
  createdBy: UserType!
}

type ReportSchedule {
  id: UUID!
  name: String!
  templateType: String!
  schedule: String!  # Cron expression
  recipients: [String!]!
  lastRunAt: DateTime
  nextRunAt: DateTime
  status: String!  # active, paused
  createdAt: DateTime!
}
```

**Required Queries:**

```graphql
# List reports
query reports($limit: Int, $offset: Int) {
  reports(limit: $limit, offset: $offset) {
    id
    name
    templateType
    status
    fileUrl
    createdAt
    createdBy { fullName }
  }
}

# List report schedules
query reportSchedules {
  reportSchedules {
    id
    name
    templateType
    schedule
    lastRunAt
    nextRunAt
    status
  }
}
```

**Required Mutations:**

```graphql
# Generate a report
mutation generateReport($input: GenerateReportInput!) {
  generateReport(input: $input) {
    id
    name
    status
    estimatedDuration
  }
}

input GenerateReportInput {
  name: String!
  templateType: String!
  sections: [String!]!
  format: String!  # pdf, excel, pptx
  dateRange: DateRangeInput
  modelIds: [UUID!]
  config: JSON
}

input DateRangeInput {
  startDate: Date!
  endDate: Date!
}
```

```graphql
# Create report schedule
mutation createReportSchedule($input: CreateReportScheduleInput!) {
  createReportSchedule(input: $input) {
    id
    name
    schedule
    nextRunAt
    status
  }
}

input CreateReportScheduleInput {
  name: String!
  templateType: String!
  sections: [String!]!
  schedule: String!  # Cron expression
  recipients: [String!]!
  format: String!
}
```

```graphql
# Update report schedule
mutation updateReportSchedule($id: UUID!, $input: UpdateReportScheduleInput!) {
  updateReportSchedule(id: $id, input: $input) {
    id
    status
    updatedAt
  }
}

input UpdateReportScheduleInput {
  name: String
  schedule: String
  recipients: [String!]
  status: String
}
```

```graphql
# Delete report schedule
mutation deleteReportSchedule($id: UUID!) {
  deleteReportSchedule(id: $id)
}
```

---

### 9. System Health & Monitoring (SystemHealth.tsx)

**Enhanced Health Query:**

```graphql
query systemHealth {
  systemHealth {
    status: String!  # healthy, degraded, unhealthy
    version: String!
    uptimeSeconds: Int!
    services: [ServiceHealth!]!
    storage: StorageInfo
    database: DatabaseInfo
  }
}

type ServiceHealth {
  name: String!
  status: String!  # healthy, degraded, unhealthy
  latency: Int  # in milliseconds
  details: JSON
}

type StorageInfo {
  totalGb: Float!
  usedGb: Float!
  availableGb: Float!
}

type DatabaseInfo {
  connectionPool: Int!
  activeConnections: Int!
  status: String!
}
```

```graphql
# List background tasks
query backgroundTasks($status: String, $limit: Int) {
  backgroundTasks(status: $status, limit: $limit) {
    id
    name
    taskType: String!
    status: String!  # pending, running, completed, failed
    progress: Int
    result: JSON
    error: String
    startedAt: DateTime
    completedAt: DateTime
    createdAt: DateTime!
  }
}
```

**Required Mutations:**

```graphql
# Cancel a background task
mutation cancelTask($id: UUID!) {
  cancelTask(id: $id)
}

# Retry a failed task
mutation retryTask($id: UUID!) {
  retryTask(id: $id) {
    id
    status
  }
}
```

---

### 10. Roles & Permissions

**Required Queries:**

```graphql
# List all roles
query roles {
  roles {
    id
    name
    description
    permissions: [String!]!
    isSystemRole: Boolean!
    createdAt: DateTime!
  }
}
```

**Required Mutations:**

```graphql
# Create role (for enterprise)
mutation createRole($input: CreateRoleInput!) {
  createRole(input: $input) {
    id
    name
    permissions
  }
}

input CreateRoleInput {
  name: String!
  description: String
  permissions: [String!]!
}
```

```graphql
# Assign role to user
mutation assignRole($userId: UUID!, $roleId: UUID!) {
  assignRole(userId: $userId, roleId: $roleId) {
    id
    roles { id name }
  }
}
```

---

## Summary: APIs Needed

### New Queries (14 total)
1. `datasets` - List datasets
2. `dataset` - Get dataset by ID
3. `dataConnectors` - List data connectors
4. `dataConnector` - Get connector by ID
5. `forecasts` - List forecasts
6. `forecast` - Get forecast by ID
7. `reports` - List reports
8. `reportSchedules` - List scheduled reports
9. `systemHealth` - Enhanced health with services
10. `backgroundTasks` - List background tasks
11. `roles` - List roles

### New Mutations (28 total)

**User Management:**
1. `createUser` - Invite user
2. `updateUser` - Update user
3. `deleteUser` - Delete user

**Organization:**
4. `updateOrganization` - Update org settings

**Authentication:**
5. `forgotPassword` - Request password reset
6. `resetPassword` - Reset with token
7. `verifyEmail` - Verify email

**Dataset:**
8. `createDataset` - Create dataset
9. `updateDataset` - Update dataset
10. `deleteDataset` - Delete dataset

**Data Connectors:**
11. `createDataConnector` - Create connector
12. `testDataConnector` - Test connection
13. `updateDataConnector` - Update connector
14. `deleteDataConnector` - Delete connector
15. `syncDataConnector` - Trigger sync

**Model:**
16. `createModel` - Create model
17. `updateModel` - Update model
18. `deleteModel` - Delete model
19. `trainModel` - Start training
20. `cancelTraining` - Cancel training
21. `promoteModelVersion` - Promote version

**Forecast:**
22. `saveForecast` - Save forecast
23. `deleteForecast` - Delete forecast

**Reports:**
24. `generateReport` - Generate report
25. `createReportSchedule` - Schedule report
26. `updateReportSchedule` - Update schedule
27. `deleteReportSchedule` - Delete schedule

**System:**
28. `cancelTask` - Cancel background task
29. `retryTask` - Retry failed task

**Roles:**
30. `createRole` - Create role
31. `assignRole` - Assign role to user

---

## Implementation Priority

### Phase 1 - Core Workflow (High Priority)
1. Dataset mutations (`createDataset`, `updateDataset`, `deleteDataset`)
2. Dataset query with details
3. Model mutations (`createModel`, `trainModel`)
4. Password reset mutations (`forgotPassword`, `resetPassword`)

### Phase 2 - Essential Features (Medium Priority)
5. User management mutations (`createUser`, `updateUser`, `deleteUser`)
6. Organization mutation (`updateOrganization`)
7. Data connector mutations (all 5)
8. Forecast mutations (`saveForecast`, `deleteForecast`)

### Phase 3 - Complete Platform (Lower Priority)
9. Report mutations (all 4)
10. System health enhancements
11. Role management mutations
12. Model version management

---

## Notes

1. **Input Types Already Defined**: The following input types are already defined in the backend but don't have corresponding mutations:
   - `CreateDatasetInput`
   - `CreateModelInput`
   - `TrainModelInput`
   - `AdstockConfigInput`
   - `SaturationConfigInput`
   - `CreateExperimentInput`
   - `CreateBudgetScenarioInput`
   - `RunOptimizationInput`
   - `WhatIfInput`

2. **REST Endpoints**: The following REST endpoints exist and can be kept as-is:
   - `POST /api/upload/data` - File upload
   - `POST /api/upload/validate` - File validation

3. **Celery Tasks**: The following background tasks exist in backend but need GraphQL exposure:
   - `train_mmm_model`
   - `run_budget_optimization`
   - `generate_report`
   - `process_scheduled_reports`

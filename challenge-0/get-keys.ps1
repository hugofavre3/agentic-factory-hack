# PowerShell equivalent of get-keys.sh
# Usage: .\get-keys.ps1 -ResourceGroup "rg-sp3-d-hfa-azu-poc_alst-txt"

param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvOut = Join-Path (Split-Path -Parent $ScriptDir) ".env"

# Check Azure login
try {
    $null = az account show 2>$null
    if ($LASTEXITCODE -ne 0) { throw }
} catch {
    Write-Host "User not signed in Azure. Sign in using 'az login' command."
    az login --use-device-code
}

# Prompt for resource group if not provided
if (-not $ResourceGroup) {
    $ResourceGroup = Read-Host "Enter the resource group name where the resources are deployed"
}

# --- Helper: run az and return trimmed string (empty string on failure) ---
function AzQuery($argList) {
    $result = & az @argList 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $result) { return "" }
    return ($result | Out-String).Trim()
}

# ── Try to get deployment name (may not exist for pre-provisioned environments) ──
Write-Host "Getting the deployments in '$ResourceGroup'..."
$deploymentName = AzQuery @("deployment", "group", "list",
    "--resource-group", $ResourceGroup,
    "--query", "[?contains(name, 'Microsoft.Template') || contains(name, 'azuredeploy') || contains(name, 'hack-deployment')].{name:name}[0].name",
    "--output", "tsv")

function DeployOutput($outputKey) {
    if (-not $deploymentName) { return "" }
    return AzQuery @("deployment", "group", "show",
        "--resource-group", $ResourceGroup,
        "--name", $deploymentName,
        "--query", "properties.outputs.$outputKey.value",
        "-o", "tsv")
}

if (-not $deploymentName) {
    Write-Host "No ARM deployment found — resources were pre-provisioned. Discovering by type..." -ForegroundColor Yellow
} else {
    Write-Host "Found deployment: $deploymentName"
}

# ── Extract deployment outputs (will be empty if no deployment) ──
Write-Host "Extracting resource names..."

$storageAccountName      = DeployOutput "storageAccountName"
$logAnalyticsWorkspaceName = DeployOutput "logAnalyticsWorkspaceName"
$searchServiceName       = DeployOutput "searchServiceName"
$aiFoundryHubName        = DeployOutput "aiFoundryHubName"
$aiFoundryProjectName    = DeployOutput "aiFoundryProjectName"
$containerRegistryName   = DeployOutput "containerRegistryName"
$applicationInsightsName = DeployOutput "applicationInsightsName"
$acrName                 = DeployOutput "acrName"
$acrUsername             = DeployOutput "acrUsername"
$acrPassword             = DeployOutput "acrPassword"
$searchServiceEndpoint   = DeployOutput "searchServiceEndpoint"
$aiFoundryHubEndpoint    = DeployOutput "aiFoundryHubEndpoint"
$aiFoundryProjectEndpoint = DeployOutput "aiFoundryProjectEndpoint"

# ── Discover missing resources by type ──
if (-not $storageAccountName -or -not $logAnalyticsWorkspaceName -or -not $containerRegistryName) {
    Write-Host "Some outputs not found, discovering resources by type..."

    if (-not $storageAccountName) {
        $storageAccountName = AzQuery @("storage","account","list","--resource-group",$ResourceGroup,"--query","[0].name","-o","tsv")
    }
    if (-not $logAnalyticsWorkspaceName) {
        $logAnalyticsWorkspaceName = AzQuery @("monitor","log-analytics","workspace","list","--resource-group",$ResourceGroup,"--query","[0].name","-o","tsv")
    }
    if (-not $searchServiceName) {
        $searchServiceName = AzQuery @("search","service","list","--resource-group",$ResourceGroup,"--query","[0].name","-o","tsv")
    }
    if (-not $aiFoundryHubName) {
        $aiFoundryHubName = AzQuery @("cognitiveservices","account","list","--resource-group",$ResourceGroup,"--query","[?kind=='AIServices'].name | [0]","-o","tsv")
    }
    if (-not $containerRegistryName) {
        $containerRegistryName = AzQuery @("acr","list","--resource-group",$ResourceGroup,"--query","[0].name","-o","tsv")
    }
    if (-not $applicationInsightsName) {
        $applicationInsightsName = AzQuery @("resource","list","--resource-group",$ResourceGroup,"--resource-type","Microsoft.Insights/components","--query","[0].name","-o","tsv")
    }
}

# Log Analytics Workspace ID
$logAnalyticsWorkspaceId = ""
if ($logAnalyticsWorkspaceName) {
    $logAnalyticsWorkspaceId = AzQuery @("monitor","log-analytics","workspace","show","--resource-group",$ResourceGroup,"--workspace-name",$logAnalyticsWorkspaceName,"--query","customerId","-o","tsv")
}

# API Management
$apiManagementName = AzQuery @("apim","list","--resource-group",$ResourceGroup,"--query","[0].name","-o","tsv")

# ── Cosmos DB ──
Write-Host "Getting Cosmos DB service information..."
$cosmosDbAccountName = DeployOutput "cosmosDbAccountName"
if (-not $cosmosDbAccountName) {
    $cosmosDbAccountName = AzQuery @("cosmosdb","list","--resource-group",$ResourceGroup,"--query","[0].name","-o","tsv")
}

$cosmosDbEndpoint = ""; $cosmosDbKey = ""; $cosmosDbConnectionString = ""
if ($cosmosDbAccountName) {
    $cosmosDbEndpoint = AzQuery @("cosmosdb","show","--name",$cosmosDbAccountName,"--resource-group",$ResourceGroup,"--query","documentEndpoint","-o","tsv")
    $cosmosDbKey      = AzQuery @("cosmosdb","keys","list","--name",$cosmosDbAccountName,"--resource-group",$ResourceGroup,"--query","primaryMasterKey","-o","tsv")
    if ($cosmosDbEndpoint -and $cosmosDbKey) {
        $cosmosDbConnectionString = "AccountEndpoint=${cosmosDbEndpoint};AccountKey=${cosmosDbKey};"
    }
} else {
    Write-Host "Warning: No Cosmos DB account found." -ForegroundColor Yellow
}

# ── Keys ──
Write-Host "Getting keys from the resources..."

# Storage
$storageAccountKey = ""; $storageAccountConnectionString = ""
if ($storageAccountName) {
    $storageAccountKey = AzQuery @("storage","account","keys","list","--account-name",$storageAccountName,"--resource-group",$ResourceGroup,"--query","[0].value","-o","tsv")
    $storageAccountConnectionString = "DefaultEndpointsProtocol=https;AccountName=${storageAccountName};AccountKey=${storageAccountKey};EndpointSuffix=core.windows.net"
}

# AI Foundry / Cognitive Services
$aiFoundryEndpoint = ""; $aiFoundryKey = ""
if ($aiFoundryHubName) {
    $aiFoundryEndpoint = AzQuery @("cognitiveservices","account","show","--name",$aiFoundryHubName,"--resource-group",$ResourceGroup,"--query","properties.endpoint","-o","tsv")
    $aiFoundryKey      = AzQuery @("cognitiveservices","account","keys","list","--name",$aiFoundryHubName,"--resource-group",$ResourceGroup,"--query","key1","-o","tsv")
}

# Search
$searchServiceKey = ""
if ($searchServiceName) {
    $searchServiceKey = AzQuery @("search","admin-key","show","--resource-group",$ResourceGroup,"--service-name",$searchServiceName,"--query","primaryKey","-o","tsv")
    if (-not $searchServiceEndpoint) {
        $searchServiceEndpoint = "https://${searchServiceName}.search.windows.net"
    }
}

# Application Insights
$appInsightsInstrumentationKey = ""; $appInsightsConnectionString = ""
if ($applicationInsightsName) {
    $appInsightsInstrumentationKey = AzQuery @("resource","show","--resource-group",$ResourceGroup,"--name",$applicationInsightsName,"--resource-type","Microsoft.Insights/components","--query","properties.InstrumentationKey","-o","tsv")
    $appInsightsConnectionString   = AzQuery @("resource","show","--resource-group",$ResourceGroup,"--name",$applicationInsightsName,"--resource-type","Microsoft.Insights/components","--query","properties.ConnectionString","-o","tsv")
}

# API Management credentials
$apimGatewayUrl = ""; $apimSubscriptionKey = ""
if ($apiManagementName) {
    Write-Host "Getting API Management credentials..."
    $apimGatewayUrl = AzQuery @("apim","show","--name",$apiManagementName,"--resource-group",$ResourceGroup,"--query","gatewayUrl","-o","tsv")
    $token = AzQuery @("account","get-access-token","--resource","https://management.azure.com","--query","accessToken","-o","tsv")
    $subId = AzQuery @("account","show","--query","id","--output","tsv")
    if ($token -and $subId) {
        $uri = "https://management.azure.com/subscriptions/$subId/resourceGroups/$ResourceGroup/providers/Microsoft.ApiManagement/service/$apiManagementName/subscriptions/master/listSecrets?api-version=2024-05-01"
        try {
            $resp = Invoke-RestMethod -Uri $uri -Method Post -Headers @{ Authorization = "Bearer $token" } -Body "" -ContentType "application/json"
            $apimSubscriptionKey = $resp.primaryKey
        } catch {
            Write-Host "Warning: Could not retrieve APIM subscription key" -ForegroundColor Yellow
        }
    }
}

# Container Registry
$acrLoginServer = ""
if ($containerRegistryName) {
    Write-Host "Getting Container Registry credentials..."
    if (-not $acrUsername -or -not $acrPassword) {
        $acrUsername = AzQuery @("acr","credential","show","--name",$containerRegistryName,"--query","username","-o","tsv")
        $acrPassword = AzQuery @("acr","credential","show","--name",$containerRegistryName,"--query","passwords[0].value","-o","tsv")
    }
    $acrLoginServer = AzQuery @("acr","show","--name",$containerRegistryName,"--resource-group",$ResourceGroup,"--query","loginServer","-o","tsv")
    if (-not $acrName) { $acrName = $containerRegistryName }
}

# ── Discover AI Foundry Project if missing ──
if (-not $aiFoundryProjectName -and $aiFoundryHubName) {
    $aiFoundryProjectName = AzQuery @("resource","list","--resource-group",$ResourceGroup,"--query","[?contains(name, 'aiproject')].name | [0]","-o","tsv")
    if (-not $aiFoundryProjectName) {
        $aiFoundryProjectName = $aiFoundryHubName -replace "-aifoundry-", "-aiproject-"
    }
}

# ── Construct IDs and endpoints ──
$subscriptionId = AzQuery @("account","show","--query","id","-o","tsv")

$azureAIConnectionId = ""
$azureAIProjectResourceId = ""
if ($aiFoundryHubName -and $searchServiceName -and $subscriptionId) {
    $azureAIConnectionId = "/subscriptions/$subscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.CognitiveServices/accounts/$aiFoundryHubName/connections/${aiFoundryHubName}-aisearch"
    $azureAIProjectResourceId = "/subscriptions/$subscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.CognitiveServices/accounts/$aiFoundryHubName/projects/$aiFoundryProjectName"
}

# AI Foundry Project Endpoint
if (-not $aiFoundryProjectEndpoint -and $aiFoundryHubName -and $aiFoundryProjectName) {
    $aiFoundryProjectEndpoint = "https://${aiFoundryHubName}.services.ai.azure.com/api/projects/${aiFoundryProjectName}"
}

# Chat endpoint for Challenge 2
$aiChatEndpoint = ""
if ($aiFoundryEndpoint) {
    $aiChatBaseEndpoint = $aiFoundryEndpoint.TrimEnd('/')
    $aiChatEndpoint = "${aiChatBaseEndpoint}/openai/deployments/gpt-4o-mini"
}

# OpenAI-style endpoint
$azureOpenAIEndpoint = ""
if ($aiFoundryHubName) {
    $azureOpenAIEndpoint = "https://${aiFoundryHubName}.openai.azure.com/"
} else {
    $azureOpenAIEndpoint = $aiFoundryEndpoint
}

# ── Write .env file ──
Write-Host "Writing .env file..."
if (Test-Path $EnvOut) { Remove-Item $EnvOut }

@"
RESOURCE_GROUP="$ResourceGroup"
AZURE_SUBSCRIPTION_ID="$subscriptionId"
AZURE_STORAGE_ACCOUNT_NAME="$storageAccountName"
AZURE_STORAGE_ACCOUNT_KEY="$storageAccountKey"
AZURE_STORAGE_CONNECTION_STRING="$storageAccountConnectionString"
LOG_ANALYTICS_WORKSPACE_NAME="$logAnalyticsWorkspaceName"
LOG_ANALYTICS_WORKSPACE_ID="$logAnalyticsWorkspaceId"
SEARCH_SERVICE_NAME="$searchServiceName"
SEARCH_SERVICE_ENDPOINT="$searchServiceEndpoint"
SEARCH_ADMIN_KEY="$searchServiceKey"
AZURE_SEARCH_ENDPOINT="$searchServiceEndpoint"
AZURE_SEARCH_API_KEY="$searchServiceKey"
AI_FOUNDRY_HUB_NAME="$aiFoundryHubName"
AI_FOUNDRY_PROJECT_NAME="$aiFoundryProjectName"
AI_FOUNDRY_ENDPOINT="$aiFoundryEndpoint"
AI_FOUNDRY_KEY="$aiFoundryKey"
AZURE_AI_CHAT_KEY="$aiFoundryKey"
AZURE_AI_CHAT_ENDPOINT="$aiChatEndpoint"
AZURE_AI_CHAT_MODEL_DEPLOYMENT_NAME="gpt-4o-mini"
AI_FOUNDRY_HUB_ENDPOINT="$aiFoundryHubEndpoint"
AI_FOUNDRY_PROJECT_ENDPOINT="$aiFoundryProjectEndpoint"
AZURE_AI_PROJECT_ENDPOINT="$aiFoundryProjectEndpoint"
AZURE_AI_PROJECT_RESOURCE_ID="$azureAIProjectResourceId"
AZURE_AI_CONNECTION_ID="$azureAIConnectionId"
AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-4.1"
EMBEDDING_MODEL_DEPLOYMENT_NAME="text-embedding-3-large"
COSMOS_NAME="$cosmosDbAccountName"
COSMOS_DATABASE_NAME="FactoryOpsDB"
COSMOS_ENDPOINT="$cosmosDbEndpoint"
COSMOS_KEY="$cosmosDbKey"
COSMOS_CONNECTION_STRING="$cosmosDbConnectionString"
APIM_NAME="$apiManagementName"
APIM_GATEWAY_URL="$apimGatewayUrl"
APIM_SUBSCRIPTION_KEY="$apimSubscriptionKey"
ACR_NAME="$acrName"
ACR_USERNAME="$acrUsername"
ACR_PASSWORD="$acrPassword"
ACR_LOGIN_SERVER="$acrLoginServer"
APPLICATION_INSIGHTS_INSTRUMENTATION_KEY="$appInsightsInstrumentationKey"
APPLICATION_INSIGHTS_CONNECTION_STRING="$appInsightsConnectionString"
APPLICATIONINSIGHTS_CONNECTION_STRING="$appInsightsConnectionString"
AZURE_OPENAI_SERVICE_NAME="$aiFoundryHubName"
AZURE_OPENAI_ENDPOINT="$azureOpenAIEndpoint"
AZURE_OPENAI_KEY="$aiFoundryKey"
AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4.1"
MODEL_DEPLOYMENT_NAME="gpt-4.1"
"@ | Set-Content -Path $EnvOut -Encoding UTF8

Write-Host ""
Write-Host "=== Configuration Summary ===" -ForegroundColor Cyan
Write-Host "Storage Account:       $storageAccountName"
Write-Host "Log Analytics:         $logAnalyticsWorkspaceName"
Write-Host "Search Service:        $searchServiceName"
Write-Host "API Management:        $apiManagementName"
Write-Host "AI Foundry Hub:        $aiFoundryHubName"
Write-Host "AI Foundry Project:    $aiFoundryProjectName"
Write-Host "Project Endpoint:      $aiFoundryProjectEndpoint"
Write-Host "Container Registry:    $containerRegistryName"
Write-Host "App Insights:          $applicationInsightsName"
Write-Host "Cosmos DB:             $cosmosDbAccountName"
Write-Host ""
Write-Host "Environment file: $EnvOut" -ForegroundColor Green

# Warn about missing services
$missing = @()
if (-not $storageAccountName)    { $missing += "Storage" }
if (-not $searchServiceName)     { $missing += "Search" }
if (-not $aiFoundryHubName)      { $missing += "AI-Foundry" }
if (-not $apiManagementName)     { $missing += "API-Management" }
if (-not $containerRegistryName) { $missing += "Container-Registry" }
if ($missing.Count -gt 0) {
    Write-Host "WARNING: Missing services: $($missing -join ', ')" -ForegroundColor Yellow
}

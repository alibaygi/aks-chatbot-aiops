output "resource_group_name" {
  description = "Name of the created resource group."
  value       = azurerm_resource_group.main.name
}

output "location" {
  description = "Azure region all resources were deployed to."
  value       = azurerm_resource_group.main.location
}

output "acr_login_server" {
  description = "Login server hostname for the container registry."
  value       = azurerm_container_registry.main.login_server
}

output "acr_id" {
  description = "Resource ID of the Azure Container Registry."
  value       = azurerm_container_registry.main.id
}

output "aks_cluster_name" {
  description = "Name of the AKS cluster."
  value       = azurerm_kubernetes_cluster.main.name
}

output "aks_cluster_id" {
  description = "Resource ID of the AKS cluster."
  value       = azurerm_kubernetes_cluster.main.id
}

output "aks_node_resource_group" {
  description = "Auto-created resource group that holds AKS node VMs and disks."
  value       = azurerm_kubernetes_cluster.main.node_resource_group
}

output "log_analytics_workspace_id" {
  description = "Resource ID of the Log Analytics workspace used for AKS diagnostics."
  value       = azurerm_log_analytics_workspace.main.id
}

output "get_credentials_command" {
  description = "Run this command to point kubectl at the new cluster."
  value       = "az aks get-credentials --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_kubernetes_cluster.main.name} --overwrite-existing"
}

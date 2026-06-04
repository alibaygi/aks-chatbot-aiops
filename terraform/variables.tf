variable "resource_group_name" {
  description = "Name of the Azure resource group."
  type        = string
  default     = "rg-gen-project"
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "germanywestcentral"
}

variable "acr_name" {
  description = "Globally unique name for the Azure Container Registry."
  type        = string
  default     = "akscontainerregistrydev"
}

variable "aks_cluster_name" {
  description = "Name of the AKS cluster."
  type        = string
  default     = "aksclusterdev"
}

variable "node_count" {
  description = "Number of nodes in the default node pool."
  type        = number
  default     = 2
}

variable "node_vm_size" {
  description = "VM size for AKS nodes."
  type        = string
  default     = "Standard_D2s_v3"
}

variable "kubernetes_version" {
  description = "Kubernetes version for the AKS cluster. null means latest stable."
  type        = string
  default     = null
}

variable "acr_sku" {
  description = "SKU for the Azure Container Registry. Basic | Standard | Premium."
  type        = string
  default     = "Basic"

  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.acr_sku)
    error_message = "acr_sku must be one of: Basic, Standard, Premium."
  }
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
  default = {
    environment = "dev"
    project     = "chatbot"
    managed_by  = "terraform"
  }
}

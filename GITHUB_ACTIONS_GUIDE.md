# How to Set Up and Run the GitHub Actions Workflow

This repo has two workflows in `.github/workflows/`:

- **pr_checks.yaml** — runs lint + tests on every pull request to `main`.
- **deploy.yml** — builds the images and deploys to AKS on every **push to `main`**.

This guide gets `deploy.yml` working: get credentials from Azure → store them as
secrets → push to deploy.

---

## 1. Create a GitHub Repository

If you haven't already:

1. Go to [github.com](https://github.com) → **New repository**
2. Name it `aks-chatbot-aiops`, set it Public or Private
3. Do **not** initialize with a README (you already have one)

Then connect your local repo and push:

```bash
git remote add origin https://github.com/alibaygi/aks-chatbot-aiops.git
git push -u origin main
```

> Pushing to `main` triggers `deploy.yml` immediately. If your Azure secrets
> aren't set up yet (steps 2–3), the run will fail at the Azure login step — that's
> expected. Finish the setup, then push again.

---

## 2. Get Credentials from Azure

The workflow logs in to Azure with **OIDC** (no password is ever stored). You run
these commands **once** from your terminal. They assume your ACR + AKS already exist
(Phase 1 of the README).

```bash
az login

# Values Azure gives you
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

# Your project values (edit GH_ORG and GH_REPO)
RESOURCE_GROUP="rg-gen-project"
AKS_CLUSTER="aksclusterdev"
ACR_NAME="akscontainerregistrydev"
GH_ORG="alibaygi"
GH_REPO="aks-chatbot-aiops"

# Create an app registration for GitHub Actions
APP_ID=$(az ad app create --display-name "github-actions-chatbot" --query appId -o tsv)
OBJECT_ID=$(az ad app show --id "$APP_ID" --query id -o tsv)
az ad sp create --id "$APP_ID"

# Trust pushes to your main branch
az ad app federated-credential create \
  --id "$OBJECT_ID" \
  --parameters "{
    \"name\": \"github-main\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:${GH_ORG}/${GH_REPO}:ref:refs/heads/main\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"

# Let the workflow push images and deploy
SP_OBJECT_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)
ACR_ID=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)
AKS_ID=$(az aks show --name "$AKS_CLUSTER" --resource-group "$RESOURCE_GROUP" --query id -o tsv)

az role assignment create --assignee-object-id "$SP_OBJECT_ID" --assignee-principal-type ServicePrincipal --role AcrPush --scope "$ACR_ID"
az role assignment create --assignee-object-id "$SP_OBJECT_ID" --assignee-principal-type ServicePrincipal --role Contributor --scope "$ACR_ID"
az role assignment create --assignee-object-id "$SP_OBJECT_ID" --assignee-principal-type ServicePrincipal --role "Azure Kubernetes Service Cluster User Role" --scope "$AKS_ID"

# Print the three values you'll paste into GitHub Secrets
echo "AZURE_CLIENT_ID:        $APP_ID"
echo "AZURE_TENANT_ID:        $TENANT_ID"
echo "AZURE_SUBSCRIPTION_ID:  $SUBSCRIPTION_ID"
```

Keep that last output — you need it in the next step.

---

## 3. Store Secrets in GitHub

Go to your repo → **Settings → Secrets and variables → Actions → Secrets tab** →
**New repository secret**, and add these:

| Secret name | Value |
|---|---|
| `AZURE_CLIENT_ID` | `$APP_ID` printed above |
| `AZURE_TENANT_ID` | `$TENANT_ID` printed above |
| `AZURE_SUBSCRIPTION_ID` | `$SUBSCRIPTION_ID` printed above |
| `HELM_VALUES_SECRETS` | Full contents of your `values-secrets.yaml` (DB password + API keys) |
| `GH_PAT` | A GitHub Personal Access Token with `contents: write` (lets the workflow push the version-bump commit) |

For `HELM_VALUES_SECRETS`, copy `k8s/aks/chart/values-secrets.yaml.example`, fill in
real values, and paste the **entire file** as the secret value:

```yaml
secrets:
  postgres:
    password: "your-strong-password"
  backend:
    secretKey: "output-of-openssl-rand-hex-32"
    openaiApiKey: "sk-..."
    tavilyApiKey: "tvly-..."
```

> Secrets are encrypted and never shown again after saving. The workflow reads them
> as `${{ secrets.AZURE_CLIENT_ID }}` etc. — GitHub injects the values at runtime.

**Optional — turn on the evaluation gate.** It's off by default. To enable it, add a
repository **variable** (Variables tab, not Secrets) named `RUN_EVAL_GATE` = `true`,
and two more secrets: `LANGSMITH_API_KEY` and `OPENAI_API_KEY`.

---

## 4. Trigger the Workflow (Push to `main`)

Unlike a release-based pipeline, this one fires on **any push to `main`**:

```bash
git add <files>
git commit -m "your message"
git push
```

That's it — `deploy.yml` starts automatically.

> The workflow ends by committing a version bump (e.g. `0.1.2` → `0.1.3`) back to
> `main` with `[skip ci]` in the message, so that commit does **not** trigger another
> run.

---

## 5. Watch the Workflow Run

1. Go to your repo → **Actions** tab
2. Click the running **Build and Deploy to AKS** workflow to open the logs
3. The steps run in order:
   - **bump version** → image tag becomes `<version>-<run_number>` (e.g. `0.1.3-42`)
   - **(optional) eval gate** → only if `RUN_EVAL_GATE = true`
   - **Azure login (OIDC)** → fails here if a secret is wrong
   - **az acr build** → builds backend + frontend images inside Azure
   - **az aks get-credentials → helm upgrade** → deploys to the cluster
   - **commit version bump** → pushes the new VERSION back to `main`

---

## 6. Verify the Deploy

After the workflow succeeds, check the cluster:

```bash
az aks get-credentials --resource-group rg-gen-project --name aksclusterdev
kubectl get pods            # frontend, backend, postgres should be Running
kubectl get svc frontend    # grab the LoadBalancer EXTERNAL-IP and open it
```

You should also see the new image tags in your registry:

```bash
az acr repository show-tags --name akscontainerregistrydev --repository chatbot/backend
```

---

## Quick Reference

```
git push to main
        ↓
GitHub Actions: deploy.yml
        ↓
bump version → (eval gate?) → Azure login (OIDC)
        ↓
az acr build backend + frontend   (builds in Azure)
        ↓
helm upgrade --install            (rolling deploy to AKS)
        ↓
commit version bump [skip ci]     (no re-trigger)
```

| Need | Where |
|---|---|
| Azure setup commands | Step 2 above (or README → Phase 2) |
| The 5 required secrets | Step 3 table |
| Trigger a deploy | `git push` to `main` |
| Watch / debug a run | Actions tab → click the run → expand the failed step |
```

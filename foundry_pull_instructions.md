# How to Pull GitHub Workflow Files into Foundry

Since we can't push directly to Foundry due to permission restrictions, follow these steps to pull the updated workflow files from GitHub into Foundry:

## In the Foundry Web Interface

1. Log in to your Foundry instance
2. Go to your repository in Foundry
3. Click on "Source Control" in the left navigation
4. Click "Pull from External Repository"
5. Configure the pull:
   - Select GitHub as the source
   - Enter your GitHub repository URL
   - Select the "clean_structure" branch
   - Select "Overwrite" for conflict resolution strategy
6. Click "Pull Changes"

## In Foundry Code Workspaces

If you're using a Foundry Code Workspace:

1. Open your terminal in the workspace
2. Run these commands:
   ```bash
   # Add GitHub as a remote (if not already added)
   git remote add github https://github.com/gsiegel14/ATLAS-EPIC.git
   
   # Fetch from GitHub
   git fetch github
   
   # Checkout the clean_structure branch
   git checkout -b clean_structure github/clean_structure
   
   # Push to Foundry's local Git repository
   git push origin clean_structure
   ```

3. After pushing, trigger a build from the Foundry UI

## After Pulling the Changes

1. Verify that the workflow files are correctly pulled by checking `.github/workflows/` directory
2. Check that the foundry.yml file is correctly pulled and contains the CI configuration
3. Trigger a build to test the CI configuration
4. If the build succeeds, you can deploy your transforms

## Troubleshooting

If the workflow files still appear empty after pulling:
1. Check file permissions in Foundry
2. Try downloading the files directly and uploading them through the Foundry UI
3. Contact your Foundry administrator for assistance with permission issues 
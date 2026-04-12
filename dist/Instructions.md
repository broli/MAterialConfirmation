# PKB Material Confirmation System - Setup Guide
**Version 2.0**

Welcome to the PKB Material Confirmation System! This application allows you to quickly generate professional, branded PDF documents for our clients based on our shared master catalog.

## Initial Setup (One-Time Only)

Before you run the application, you need to connect your computer to the PKB Shared Master Database. 

### Step 1: Sync the Database to your PC
1. Open your web browser and navigate to the **PKB Team SharePoint** site.
2. Go to the **Documents** library where the `PKB Master Database` folder is located.
3. Click the **"Sync"** or **"Add shortcut to OneDrive"** button at the top of the webpage.
4. Open your computer's File Explorer. You should now see the synced folder under your company's OneDrive section.

### Step 2: Link the Application
1. Double-click the `PKB Material Confirmation System_v2.0.exe` file to launch the app.
   *(Note: If Windows Defender shows a blue "Windows protected your PC" screen, click **More info** and then **Run anyway**. This only happens the very first time).*
2. A welcome prompt will appear asking you to link the database. Click **OK**.
3. A file browser will open. Navigate to the synced SharePoint folder you created in Step 1.
4. **Important:** Select the folder that contains the file named `README_PKB_DATABASE.txt`. 
5. Click **Select Folder**.

The application will save this location. You will not have to do this again unless you move or delete the folder.

---

## How to Use the System

### Generating a Client PDF
1. Open the **Document Generator** tab.
2. Enter the Client's Name and Project Address on the left sidebar.
3. Use the search bar in the middle to find products by Brand, Model, Type, Finish, or Size.
4. Click on a product to add it to the Client Selection list on the right.
5. *(Optional)* Click **Attach Image/Page...** to add custom AutoCAD drawings or special invoices to the end of the PDF. You can type a custom title for each attachment.
6. Click **Generate PDF**. The final document will be saved to the `output/` folder located wherever you saved the `.exe` file.

### Updating the Master Catalog
If you need to add a new product or fix a typo, click the **Catalog Manager** tab.
* **To Add:** Fill out the form on the right and click "Save to Database".
* **To Edit/Delete:** Click any existing item in the Database Browser list on the left. A window will pop up showing the item's details and photo, giving you the option to Edit or Delete it.

*Note: Any changes made in the Catalog Manager are instantly synced to the SharePoint cloud and will update for the rest of the team automatically.*
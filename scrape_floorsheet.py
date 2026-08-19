from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    UnexpectedAlertPresentException,
    NoAlertPresentException,
)

from bs4 import BeautifulSoup

from datetime import datetime
import pandas as pd
import os
import sys
import time


# ============================================================
# CONFIGURATION
# ============================================================

URL = "https://merolagani.com/Floorsheet.aspx"

TABLE_CLASS = "table table-bordered table-striped table-hover sortable"

OUTPUT_DIR = "data"

PAGE_LOAD_TIMEOUT = 240
WAIT_TIMEOUT = 20


# ============================================================
# CREATE CHROME DRIVER
# ============================================================

def create_driver():
    """
    Create and configure a headless Chrome WebDriver.

    Designed for:
        - Local execution
        - GitHub Actions
        - Modern Chrome / Selenium 4
    """

    options = Options()

    # --------------------------------------------------------
    # Headless Chrome
    # --------------------------------------------------------

    options.add_argument("--headless=new")

    # --------------------------------------------------------
    # Required for GitHub Actions / Linux
    # --------------------------------------------------------

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # --------------------------------------------------------
    # Chrome stability
    # --------------------------------------------------------

    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")

    # --------------------------------------------------------
    # Disable browser notifications
    # --------------------------------------------------------

    options.add_argument("--disable-notifications")

    # --------------------------------------------------------
    # Disable notification permission requests
    #
    # 1 = allow
    # 2 = block
    # --------------------------------------------------------

    prefs = {
        "profile.default_content_setting_values.notifications": 2
    }

    options.add_experimental_option(
        "prefs",
        prefs
    )

    # --------------------------------------------------------
    # Automatically dismiss unexpected JavaScript alerts
    # --------------------------------------------------------

    options.set_capability(
        "unhandledPromptBehavior",
        "dismiss"
    )

    # --------------------------------------------------------
    # Reduce Chrome logging
    # --------------------------------------------------------

    options.add_argument("--log-level=3")

    # --------------------------------------------------------
    # Create driver
    # --------------------------------------------------------

    driver = webdriver.Chrome(
        options=options
    )

    driver.set_page_load_timeout(
        PAGE_LOAD_TIMEOUT
    )

    return driver


# ============================================================
# DISMISS ALERT
# ============================================================

def dismiss_alert(driver):
    """
    Check for an active JavaScript/browser alert
    and dismiss it.

    Returns:
        True  -> alert was found and dismissed
        False -> no alert was present
    """

    try:

        alert = driver.switch_to.alert

        print(
            f"Browser alert detected: {alert.text}"
        )

        alert.dismiss()

        print("Browser alert dismissed.")

        return True

    except NoAlertPresentException:

        return False

    except Exception as e:

        print(
            f"Could not dismiss alert: {e}"
        )

        return False


# ============================================================
# SAFE CLICK
# ============================================================

def safe_click(driver, element):
    """
    Click an element while safely handling unexpected alerts.
    """

    try:

        element.click()

    except UnexpectedAlertPresentException:

        print(
            "Unexpected alert appeared during click."
        )

        dismiss_alert(driver)

        # Try the click again
        try:

            driver.execute_script(
                "arguments[0].click();",
                element
            )

        except Exception as e:

            print(
                f"Could not click element after dismissing alert: {e}"
            )

            raise

    # Handle an alert that appeared after clicking
    dismiss_alert(driver)


# ============================================================
# SEARCH FLOOR SHEET
# ============================================================

def search(driver, date):
    """
    Search Merolagani floorsheet for a given date.

    Date format:
        mm/dd/yyyy
    """

    print(
        "Opening Merolagani Floorsheet..."
    )

    print(
        f"Searching date: {date}"
    )

    # --------------------------------------------------------
    # Open website
    # --------------------------------------------------------

    try:

        driver.get(URL)

    except UnexpectedAlertPresentException:

        print(
            "Alert appeared while opening the website."
        )

        dismiss_alert(driver)

    # --------------------------------------------------------
    # Dismiss any initial alert
    # --------------------------------------------------------

    dismiss_alert(driver)

    # --------------------------------------------------------
    # Find date input
    # --------------------------------------------------------

    try:

        date_input = WebDriverWait(
            driver,
            WAIT_TIMEOUT
        ).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/form/div[4]/div[4]/div/div/div[1]/div[4]/input"
                )
            )
        )

    except UnexpectedAlertPresentException:

        print(
            "Alert appeared while locating date input."
        )

        dismiss_alert(driver)

        date_input = WebDriverWait(
            driver,
            WAIT_TIMEOUT
        ).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/form/div[4]/div[4]/div/div/div[1]/div[4]/input"
                )
            )
        )

    # --------------------------------------------------------
    # Find search button
    # --------------------------------------------------------

    search_btn = WebDriverWait(
        driver,
        WAIT_TIMEOUT
    ).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "/html/body/form/div[4]/div[4]/div/div/div[2]/a[1]"
            )
        )
    )

    # --------------------------------------------------------
    # Enter date
    # --------------------------------------------------------

    dismiss_alert(driver)

    date_input.clear()

    date_input.send_keys(
        date
    )

    print(
        "Submitting search..."
    )

    # --------------------------------------------------------
    # CLICK SEARCH
    #
    # This is where your original code was failing.
    # The Merolagani notification alert can appear here.
    # --------------------------------------------------------

    safe_click(
        driver,
        search_btn
    )

    # --------------------------------------------------------
    # Give website time to process request
    # --------------------------------------------------------

    time.sleep(2)

    # --------------------------------------------------------
    # Dismiss any alert after search
    # --------------------------------------------------------

    dismiss_alert(driver)

    # --------------------------------------------------------
    # Check for "no data" message
    # --------------------------------------------------------

    try:

        WebDriverWait(
            driver,
            5
        ).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//*[contains(text(), "
                    "'Could not find floorsheet matching the search criteria')]"
                )
            )
        )

        print(
            "No data found for the given date."
        )

        return False

    except TimeoutException:

        pass

    print(
        "Search completed."
    )

    return True


# ============================================================
# GET TABLE FROM CURRENT PAGE
# ============================================================

def get_page_table(driver):
    """
    Extract the floorsheet table from the current page.
    """

    # --------------------------------------------------------
    # Dismiss any active alert
    # --------------------------------------------------------

    dismiss_alert(driver)

    print(
        "Waiting for floorsheet table..."
    )

    # --------------------------------------------------------
    # Wait for table
    # --------------------------------------------------------

    try:

        WebDriverWait(
            driver,
            WAIT_TIMEOUT
        ).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/form/div[4]/div[5]/div/div[4]/table"
                )
            )
        )

    except UnexpectedAlertPresentException:

        print(
            "Alert appeared while waiting for table."
        )

        dismiss_alert(driver)

        WebDriverWait(
            driver,
            WAIT_TIMEOUT
        ).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/form/div[4]/div[5]/div/div[4]/table"
                )
            )
        )

    # --------------------------------------------------------
    # Get page source
    # --------------------------------------------------------

    dismiss_alert(driver)

    soup = BeautifulSoup(
        driver.page_source,
        "html.parser"
    )

    # --------------------------------------------------------
    # Find table
    # --------------------------------------------------------

    table = soup.find(
        "table",
        {
            "class": TABLE_CLASS
        }
    )

    if table is None:

        raise RuntimeError(
            "Floorsheet table could not be found."
        )

    # --------------------------------------------------------
    # Extract rows
    # --------------------------------------------------------

    tab_data = []

    for row in table.find_all("tr"):

        cells = row.find_all(
            ["th", "td"]
        )

        row_data = []

        for cell in cells:

            value = cell.get_text(
                strip=True
            )

            row_data.append(
                value
            )

        if row_data:

            tab_data.append(
                row_data
            )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    if not tab_data:

        raise RuntimeError(
            "Floorsheet table contains no data."
        )

    return pd.DataFrame(
        tab_data
    )


# ============================================================
# SCRAPE ALL PAGES
# ============================================================

def scrape_data(driver, date):
    """
    Search and scrape all floorsheet pages.
    """

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    found = search(
        driver,
        date
    )

    if not found:

        return pd.DataFrame()

    # --------------------------------------------------------
    # Store all pages
    # --------------------------------------------------------

    all_pages = []

    page_number = 0

    # --------------------------------------------------------
    # Pagination loop
    # --------------------------------------------------------

    while True:

        page_number += 1

        print()
        print(
            f"Scraping page {page_number}..."
        )

        # ----------------------------------------------------
        # Scrape current page
        # ----------------------------------------------------

        try:

            page_table_df = get_page_table(
                driver
            )

            print(
                f"Rows found on page {page_number}: "
                f"{len(page_table_df)}"
            )

            all_pages.append(
                page_table_df
            )

        except Exception as e:

            print()
            print(
                f"Error scraping page {page_number}: {e}"
            )

            break

        # ----------------------------------------------------
        # Find Next button
        # ----------------------------------------------------

        dismiss_alert(driver)

        try:

            next_btn = driver.find_element(
                By.LINK_TEXT,
                "Next"
            )

            # ------------------------------------------------
            # Check if disabled
            # ------------------------------------------------

            classes = (
                next_btn.get_attribute(
                    "class"
                ) or ""
            )

            aria_disabled = (
                next_btn.get_attribute(
                    "aria-disabled"
                ) or ""
            )

            if (
                "disabled" in classes.lower()
                or aria_disabled.lower() == "true"
            ):

                print(
                    "Next button is disabled."
                )

                break

            # ------------------------------------------------
            # Click next
            # ------------------------------------------------

            print(
                "Moving to next page..."
            )

            safe_click(
                driver,
                next_btn
            )

            # ------------------------------------------------
            # Wait for page update
            # ------------------------------------------------

            time.sleep(1)

        except NoSuchElementException:

            print(
                "No more pages found."
            )

            break

        except UnexpectedAlertPresentException:

            print(
                "Unexpected alert appeared while moving "
                "to the next page."
            )

            dismiss_alert(driver)

            # Try finding Next again
            try:

                next_btn = driver.find_element(
                    By.LINK_TEXT,
                    "Next"
                )

                driver.execute_script(
                    "arguments[0].click();",
                    next_btn
                )

                time.sleep(1)

            except Exception as e:

                print(
                    f"Could not continue pagination: {e}"
                )

                break

        except Exception as e:

            print(
                f"Could not move to next page: {e}"
            )

            break

    # --------------------------------------------------------
    # Combine pages
    # --------------------------------------------------------

    if not all_pages:

        return pd.DataFrame()

    print()
    print(
        f"Combining {len(all_pages)} pages..."
    )

    df = pd.concat(
        all_pages,
        ignore_index=True
    )

    return df


# ============================================================
# CLEAN DATA
# ============================================================

def clean_df(df):
    """
    Clean scraped floorsheet dataframe.
    """

    if df.empty:

        print(
            "DataFrame is empty."
        )

        return df

    print(
        "Cleaning dataframe..."
    )

    # --------------------------------------------------------
    # Remove duplicate rows
    # --------------------------------------------------------

    new_df = (
        df
        .drop_duplicates(
            keep="first"
        )
        .copy()
    )

    # --------------------------------------------------------
    # First row becomes header
    # --------------------------------------------------------

    new_header = new_df.iloc[0]

    new_df = (
        new_df
        .iloc[1:]
        .copy()
    )

    new_df.columns = new_header

    # --------------------------------------------------------
    # Remove "#" column
    # --------------------------------------------------------

    if "#" in new_df.columns:

        new_df.drop(
            columns=["#"],
            inplace=True
        )

    # --------------------------------------------------------
    # Clean Rate
    # --------------------------------------------------------

    if "Rate" in new_df.columns:

        new_df["Rate"] = (
            new_df["Rate"]
            .astype(str)
            .str.replace(
                ",",
                "",
                regex=False
            )
            .str.strip()
        )

        new_df["Rate"] = pd.to_numeric(
            new_df["Rate"],
            errors="coerce"
        )

    # --------------------------------------------------------
    # Clean Amount
    # --------------------------------------------------------

    if "Amount" in new_df.columns:

        new_df["Amount"] = (
            new_df["Amount"]
            .astype(str)
            .str.replace(
                ",",
                "",
                regex=False
            )
            .str.strip()
        )

        new_df["Amount"] = pd.to_numeric(
            new_df["Amount"],
            errors="coerce"
        )

    # --------------------------------------------------------
    # Reset index
    # --------------------------------------------------------

    new_df.reset_index(
        drop=True,
        inplace=True
    )

    return new_df


# ============================================================
# SAVE DATA
# ============================================================

def save_data(df, date):
    """
    Save dataframe to CSV.
    """

    if df.empty:

        print(
            "No data to save."
        )

        return None

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Create filename
    # --------------------------------------------------------

    file_name = date.replace(
        "/",
        "_"
    )

    file_path = os.path.join(
        OUTPUT_DIR,
        f"{file_name}.csv"
    )

    # --------------------------------------------------------
    # Save CSV
    # --------------------------------------------------------

    df.to_csv(
        file_path,
        index=False
    )

    print()
    print("=" * 60)
    print(
        "DATA SAVED SUCCESSFULLY"
    )
    print("=" * 60)

    print(
        f"File: {file_path}"
    )

    print(
        f"Rows: {len(df)}"
    )

    print(
        f"Columns: {len(df.columns)}"
    )

    print("=" * 60)

    return file_path


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print(
        "MEROLAGANI FLOORSHEET SCRAPER"
    )
    print("=" * 60)

    # --------------------------------------------------------
    # Today's date
    # --------------------------------------------------------

    date = datetime.today().strftime(
        "%m/%d/%Y"
    )

    print(
        f"Date: {date}"
    )

    driver = None

    try:

        # ----------------------------------------------------
        # Start browser
        # ----------------------------------------------------

        print(
            "Starting Chrome..."
        )

        driver = create_driver()

        # ----------------------------------------------------
        # Scrape
        # ----------------------------------------------------

        df = scrape_data(
            driver,
            date
        )

        # ----------------------------------------------------
        # Check result
        # ----------------------------------------------------

        if df.empty:

            print()
            print(
                "No floorsheet data found."
            )

            print(
                "Script finished."
            )

            return

        # ----------------------------------------------------
        # Clean
        # ----------------------------------------------------

        final_df = clean_df(
            df
        )

        # ----------------------------------------------------
        # Save
        # ----------------------------------------------------

        save_data(
            final_df,
            date
        )

    except Exception as e:

        print()
        print("=" * 60)
        print(
            "ERROR"
        )
        print("=" * 60)

        print(
            f"{type(e).__name__}: {e}"
        )

        print("=" * 60)

        sys.exit(1)

    finally:

        # ----------------------------------------------------
        # Always close browser
        # ----------------------------------------------------

        if driver is not None:

            try:

                driver.quit()

                print(
                    "Chrome closed."
                )

            except Exception:

                pass

    print()
    print(
        "Script completed successfully."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
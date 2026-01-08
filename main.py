from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.common.exceptions import TimeoutException

import os

def scrape_idaho_courts(search_name):
    """
    Scrapes the Idaho courts website for a given name, including handling pagination.
    """
    driver = webdriver.Firefox()
    wait = WebDriverWait(driver, 20)
    all_results = [] # To store all extracted cases

    try:
        driver.get("https://mycourts.idaho.gov/odysseyportal/")

        # Click "Smart Search" link
        smart_search_link = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[3]/div/div[1]/a")))
        smart_search_link.click()

        search_input = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='caseCriteria_SearchCriteria']")))
        search_input.send_keys(search_name)

        print("Please solve the CAPTCHA in the browser.")
        input("Press Enter to continue after solving the CAPTCHA...")

        print("Minimizing the browser window.")
        driver.minimize_window()

        submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='btnSSSubmit']")))
        submit_button.click()

        page_num = 1
        while True:
            print(f"Scraping page {page_num} of party results...")
            main_grid_tbody_xpath = "//div[@id='Grid']/table/tbody"
            no_results_xpath = "//div[@id='partyNoResults' and not(contains(@style, 'display: none'))]"

            try:
                # Wait for either the results grid or the "no results" message to appear
                wait.until(EC.any_of(
                    EC.presence_of_element_located((By.XPATH, main_grid_tbody_xpath)),
                    EC.visibility_of_element_located((By.XPATH, no_results_xpath))
                ))

                # Check if the "no results" message is displayed
                if len(driver.find_elements(By.XPATH, no_results_xpath)) > 0:
                    print("No search results matched your selection criteria.")
                    break # Exit the while loop
                
                # If we're here, the results grid is present, so we get the rows
                party_rows = driver.find_elements(By.XPATH, f"{main_grid_tbody_xpath}/tr[contains(@class, 'k-master-row')]")

            except TimeoutException:
                print("Timeout waiting for search results or 'no results' message.")
                break # Exit the while loop

            if not party_rows and page_num == 1:
                print("No party results found.")
                break
            elif not party_rows: # No more parties on subsequent pages
                break

            for party_row in party_rows:
                # Find the party name from the main grid
                try:
                    party_name_in_main_grid = party_row.find_element(By.XPATH, ".//a[@class='partyDataLink']").text
                    print(f"  Processing party: {party_name_in_main_grid}")
                except:
                    party_name_in_main_grid = "N/A" # Fallback if party name not found
                    print(f"  Processing party (name not found in main grid): N/A")

                # Click the expand button to show the detailed cases for this party
                # Use a try-except block here as some rows might not have an expand button or it might not be clickable
                try:
                    expand_button = party_row.find_element(By.XPATH, ".//a[contains(@class, 'k-icon k-minus') or contains(@class, 'k-icon k-plus')]")
                    if "k-plus" in expand_button.get_attribute("class"): # Only click if not already expanded
                        expand_button.click()
                        time.sleep(1) # Give it a moment to expand
                except Exception as e:
                    print(f"    Could not click expand button for party: {party_name_in_main_grid}. Error: {e}")
                    continue # Skip to next party if cannot expand

                try:
                    party_uid = party_row.get_attribute("data-uid")
                    # This XPath uniquely identifies the nested case table for the current party
                    unique_case_table_body_xpath = f"//tr[@data-uid='{party_uid}']/following-sibling::tr[1]//div[contains(@class, 'party-results-container')]//table/tbody"

                    # Wait for the nested table to be visible
                    nested_case_tbody = wait.until(EC.visibility_of_element_located((By.XPATH, unique_case_table_body_xpath)))
                    
                    nested_case_rows = nested_case_tbody.find_elements(By.XPATH, "./tr[contains(@class, 'k-master-row')]")

                    for case_row in nested_case_rows:
                        try:
                            case_number_element = case_row.find_element(By.XPATH, ".//td[2]/a")
                            case_number = case_number_element.text
                            case_link = case_number_element.get_attribute("href")
                            case_type = case_row.find_element(By.XPATH, ".//td[3]").text
                            location = case_row.find_element(By.XPATH, ".//td[4]").text
                            party_name = case_row.find_element(By.XPATH, ".//td[5]").text

                            all_results.append({
                                "Case Number": case_number,
                                "Case Link": case_link,
                                "Type": case_type,
                                "Location": location,
                                "Party Name": party_name
                            })
                        except Exception as e:
                            print(f"    Error extracting data from a nested case row for party {party_name_in_main_grid}: {e}")
                except Exception as e:
                    print(f"    Could not find or process nested case table for party {party_name_in_main_grid}: {e}")
            
            # Check for next page button in the main pager
            pager_xpath = "//div[contains(@class, 'k-pager-wrap') and contains(@class, 'k-grid-pager')]"
            next_button_xpath = f"{pager_xpath}//a[contains(@class, 'k-i-arrow-e') and not(contains(@class, 'k-state-disabled'))]"
            
            try:
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, next_button_xpath)))
                next_button.click()
                page_num += 1
                time.sleep(2) # Wait for the next page to load
            except:
                print("No more pages of party results.")
                break

        if all_results:
            file_name = f"{search_name.replace(' ', '_')}_results.txt"
            with open(file_name, "w", encoding="utf-8") as f:
                for result in all_results:
                    f.write(f"Case Number: {result['Case Number']}\n")
                    f.write(f"Case Link: {result['Case Link']}\n")
                    f.write(f"Type: {result['Type']}\n")
                    f.write(f"Location: {result['Location']}\n")
                    f.write(f"Party Name: {result['Party Name']}\n")
                    f.write("-" * 30 + "\n")
            print(f"All {len(all_results)} results saved to {file_name}")
        else:
            print("No results to save.")

    finally:
        print("Script finished. Closing browser.")
        driver.quit()

if __name__ == "__main__":
    search_name = input("Enter the name to search for: ")
    scrape_idaho_courts(search_name)
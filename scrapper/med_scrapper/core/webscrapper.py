import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from .models import *

# Create your views here. # This comment seems misplaced if this is a scraper module

URLS = "https://products.mhra.gov.uk/"

def get_webdriver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4556.108 Safari/537.36') # Updated user agent
    # options.add_experimental_option("excludeSwitches", ["enable-automation"])
    # options.add_experimental_option('useAutomationExtension', False)

    try:
        # Use webdriver-manager to handle driver download/path
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        return driver
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        return None


def scrape_search(query_text, search_query_instance, website_instance):
    """
    Performs a search on the MHRA website, handles pagination, and saves results to the database.

    Args:
        query_text (str): The product name to search for.
        search_query_instance (SearchQuery): The Django SearchQuery model instance for this search.
        website_instance (Website): The Django Website model instance for MHRA.

    Returns:
        list: A list of created SearchResult objects.
        str: An error message if scraping failed, otherwise None.
    """
    driver = None
    all_results = []
    error_message = None
    current_page = 1
    # Keep track of the global position across all pages
    global_position_counter = 0

    try:
        driver = get_webdriver()
        if not driver:
            return [], "Failed to get webdriver"

        wait = WebDriverWait(driver, 30) # Increased wait time for robustness

        print(f"Scraping MHRA for: {query_text}")
        driver.get(URLS)

        # --- Step 1: Handle Initial Search Page ---
        print("Attempting to find search bar...")
        # Verified locators based on previous template
        search_input_locator = (By.ID, 'search')
        search_button_locator = (By.CSS_SELECTOR, 'form[role="search"] input[type="submit"]')

        try:
            # Add a small buffer before looking for elements
            time.sleep(1)
            search_input = wait.until(EC.presence_of_element_located(search_input_locator))
            search_button = wait.until(EC.element_to_be_clickable(search_button_locator))

            search_input.send_keys(query_text)
            print(f"Entered query: '{query_text}'")

            search_button.click()
            print("Clicked search button.")

        except (TimeoutException, NoSuchElementException) as e:
            error_message = f"Could not find search input or button on MHRA search page: {e}"
            print(error_message)
            return [], error_message # Exit if search fails

        # --- Step 2: Handle Disclaimer Page (Conditional) ---
        disclaimer_checkbox_locator = (By.ID, 'agree-checkbox')
        disclaimer_button_locator = (By.XPATH, '//button[text()="Agree" and @type="submit"]')

        try:
            # Use a shorter wait specifically for the disclaimer elements
            disclaimer_wait = WebDriverWait(driver, 5)
            disclaimer_wait.until(EC.presence_of_element_located(disclaimer_checkbox_locator))
            print("Disclaimer page detected. Attempting to agree...")

            # Use the main wait for clicking, as elements should be present now
            agree_checkbox = wait.until(EC.element_to_be_clickable(disclaimer_checkbox_locator))

            # Check if the checkbox is not already selected before clicking
            if not agree_checkbox.is_selected():
                 agree_checkbox.click()
                 time.sleep(1)
                 print("Ticked disclaimer checkbox.")
                 
            agree_button = wait.until(EC.element_to_be_clickable(disclaimer_button_locator))
            agree_button.click()
            print("Clicked Agree button.")

            # Wait for an element expected on the results page after agreeing
            results_section_locator = (By.CSS_SELECTOR, 'section.column.results')
            wait.until(EC.presence_of_element_located(results_section_locator))
            print("Navigated past disclaimer to results page.")

        except TimeoutException:
            # If timeout occurs, disclaimer elements didn't appear within the short wait
            print("Disclaimer page not detected (or already accepted). Proceeding...")
            pass # Disclaimer page was not present, continue to results page handling
        
        except (NoSuchElementException, ElementClickInterceptedException) as e:
             error_message = f"Error interacting with disclaimer page elements: {e}"
             print(error_message)
             # Decide if this is a critical error preventing scraping
             # For now, let's assume it is and exit
             return [], error_message
        except Exception as e:
            error_message = f"An unexpected error occurred on the disclaimer step: {e}"
            print(error_message)
            return [], error_message

        # --- Step 3: Handle Results Page and Pagination ---
        print("Attempting to extract search results...")
        # More specific locator for the results container
        results_section_locator = (By.CSS_SELECTOR, 'section.column.results')
        results_container_locator = (By.CSS_SELECTOR, 'dl') # The <dl> contains all results within the section
        result_item_locator = (By.CSS_SELECTOR, '.search-result') # Each <div class="search-result"> within the dl
        next_button_locator = (By.XPATH, '//nav[@aria-label="Pagination Navigation"]//button[@class="arrow" and text()="Next"]')
        # Locator to check if the Next button is disabled (indicating last page)
        next_button_disabled_locator = (By.XPATH, '//nav[@aria-label="Pagination Navigation"]//button[@class="arrow" and text()="Next" and @disabled]')


        while True: # Loop through pages
            print(f"Scraping results from page {current_page}...")
            page_results = [] # Store results for the current page temporarily

            try:
                # Wait for the results section first, then find the dl within it
                results_section = wait.until(EC.presence_of_element_located(results_section_locator))
                results_container = results_section.find_element(*results_container_locator)

                # Add a small pause after the container is found, in case results populate dynamically
                time.sleep(2) # Adjust as needed

                result_elements = results_container.find_elements(*result_item_locator)

                if not result_elements:
                    print(f"No results found on page {current_page}.")
                    # If no results on page 1, maybe the search returned nothing
                    if current_page == 1:
                         return [], "No results found for the initial search."
                    else:
                         # If no results on subsequent pages, it means we've likely reached the end
                         break # Exit pagination loop

                print(f"Found {len(result_elements)} search results on page {current_page}")

                for position_on_page, element in enumerate(result_elements):
                    try:
                        # Locators relative to the current 'element' (.search-result div)
                        link_locator = (By.CSS_SELECTOR, 'dd.right a')
                        title_locator = (By.CSS_SELECTOR, 'dd.right a p.title')
                        subtitle_locator = (By.CSS_SELECTOR, 'dd.right a p.subtitle')

                        link_element = element.find_element(*link_locator)
                        product_url = link_element.get_attribute('href')

                        title_element = element.find_element(*title_locator)
                        subtitle_element = element.find_element(*subtitle_locator)
                        full_title = f"{title_element.text.strip()} - {subtitle_element.text.strip()}"

                        # Increment global position counter
                        global_position_counter += 1

                        # --- Save Result to Database ---
                        search_result = SearchResult(
                            search_query = search_query_instance,
                            website = website_instance,
                            title = full_title, # Using combined title and subtitle
                            product_url = product_url,
                            position = global_position_counter, # Use global position
                        )
                        search_result.save()
                        all_results.append(search_result) # Add to the list returned by the function
                        # print(f"  Saved result {search_result.position}: {full_title[:80]}...") # Keep minimal console output

                    except (NoSuchElementException, Exception) as e:
                        print(f"  Error extracting data from result item at page {current_page}, position {position_on_page + 1}: {e}")
                        # Continue to the next result item even if one fails

            except TimeoutException:
                error_message = f"Timed out waiting for search results container on page {current_page}. Page content might not have loaded correctly."
                print(error_message)
                break # Exit pagination loop on timeout

            except Exception as e:
                error_message = f"An unexpected error occurred during results extraction on page {current_page}: {e}"
                print(error_message)
                break # Exit pagination loop on unexpected error

            # --- Pagination Logic ---
            # Check if the 'Next' button is present and enabled
            next_button = None
            try:
                # Use a short wait to find the Next button
                next_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable(next_button_locator))
                # Also check if it's disabled (indicating the last page)
                WebDriverWait(driver, 1).until_not(EC.presence_of_element_located(next_button_disabled_locator))
                print("Next button found and is clickable.")

            except (TimeoutException, NoSuchElementException):
                # If the button is not found or not clickable within the short wait,
                # it's likely the last page or pagination is missing.
                print('Next button not found or not clickable. Assuming last page.')
                break # Exit pagination loop

            except Exception as e:
                 # Catch any other errors while looking for the next button
                 print(f"An unexpected error occurred while checking for 'Next' button: {e}")
                 break # Exit pagination loop


            # If Next button was found and is clickable, click it
            try:
                next_button.click()
                print(f"Clicked 'Next'. Moving to page {current_page + 1}.")
                current_page += 1
                # Add a small delay after clicking next to allow the next page to start loading
                time.sleep(2) # Adjust as needed

                # Wait for the results container to be present on the *new* page
                # This is important to ensure the page has loaded before trying to find results again
                wait.until(EC.presence_of_element_located(results_section_locator))
                print(f"Successfully loaded page {current_page}.")

            except ElementClickInterceptedException as e:
                error_message = f"Click on 'Next' button intercepted on page {current_page}. An overlay might be blocking it: {e}"
                print(error_message)
                break # Exit pagination loop if click fails
            except TimeoutException:
                 error_message = f"Timed out waiting for results section to appear after clicking 'Next' on page {current_page}. Page might not have loaded."
                 print(error_message)
                 break # Exit pagination loop if next page doesn't load
            except Exception as e:
                error_message = f"An unexpected error occurred clicking 'Next' on page {current_page}: {e}"
                print(error_message)
                break # Exit pagination loop on unexpected error

    except Exception as e:
        # Catch any exceptions during initial page load or setup before the pagination loop
        error_message = f"An overall error occurred during MHRA scraping: {e}"
        print(error_message)

    finally:
        if driver:
            driver.quit() # Always close the browser

    # Return the list of all saved results and any error message encountered
    return all_results, error_message

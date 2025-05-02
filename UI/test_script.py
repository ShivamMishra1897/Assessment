from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy, ProxyType

# Replace with your actual proxy details
proxy_host = "YOUR_UK_PROXY_IP_OR_HOSTNAME"
proxy_port = YOUR_UK_PROXY_PORT
proxy_username = "YOUR_PROXY_USERNAME"  # Optional
proxy_password = "YOUR_PROXY_PASSWORD"  # Optional

# Configure the proxy
proxy = Proxy()
proxy.proxy_type = ProxyType.MANUAL
proxy.http_proxy = f"{proxy_host}:{proxy_port}"
proxy.ssl_proxy = f"{proxy_host}:{proxy_port}"  # Often the same for HTTP and HTTPS

# If your proxy requires authentication
if proxy_username and proxy_password:
    proxy.proxy_username = proxy_username
    proxy.proxy_password = proxy_password

# Set Chrome options and add the proxy
chrome_options = webdriver.ChromeOptions()
chrome_options.proxy = proxy

# Initialize the Chrome driver with the configured options
driver = webdriver.Chrome(options=chrome_options)

try:
    # Navigate to the desired URL
    url = "https://www.medicines.org.uk/emc/"  
    driver.get(url)

    print(f"Page title: {driver.title}")

    # Optional: Print the IP address detected by the website
    ip_element = driver.find_element("xpath", "//div[@id='ipv4']/a")
    print(f"Detected IP address: {ip_element.text}")

finally:
    # Close the browser
    driver.quit()
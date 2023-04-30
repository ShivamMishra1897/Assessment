class Banker:
    def __init__(self, name, id, balance):
        self.name = name
        self.id = id
        self.balance = balance

class Customer:
    def __init__(self, name, id, account_type):
        self.name = name
        self.id = id
        self.account_type = account_type

class BankManagement:
    def __init__(self):
        self.bankers = []
        self.customers = []
    
    def add_banker(self, banker):
        # Method to add a banker to the list of bankers
        self.bankers.append(banker)
        print(f"{banker.name} added as banker with ID {banker.id}")
    
    def add_customer(self, customer):
        # Method to add a customer to the list of customers
        self.customers.append(customer)
        print(f"{customer.name} added as customer with ID {customer.id}")
    
    def view_all_bankers(self):
        # Method to view all bankers in the bank management system
        print("All Bankers:")
        for banker in self.bankers:
            print(f"{banker.name} - ID: {banker.id}, Balance: {banker.balance}")
    
    def view_all_customers(self):
        # Method to view all customers in the bank management system
        print("All Customers:")
        for customer in self.customers:
            print(f"{customer.name} - ID: {customer.id}, Account Type: {customer.account_type}")

bank_management = BankManagement()

# Interactive console input to add bankers and customers
while True:
    print("Choose an option:")
    print("1. Add Banker")
    print("2. Add Customer")
    print("3. View All Bankers")
    print("4. View All Customers")
    print("5. Exit")
    choice = input("Enter your choice: ")
    
    if choice == "1":
        name = input("Enter banker name: ")
        id = input("Enter banker ID: ")
        balance = input("Enter banker balance: ")
        banker = Banker(name, id, balance)
        bank_management.add_banker(banker)
    
    elif choice == "2":
        name = input("Enter customer name: ")
        id = input("Enter customer ID: ")
        account_type = input("Enter account type: ")
        customer = Customer(name, id, account_type)
        bank_management.add_customer(customer)
    
    elif choice == "3":
        bank_management.view_all_bankers()
    
    elif choice == "4":
        bank_management.view_all_customers()
    
    elif choice == "5":
        print("Exiting...")
        break
    
    else:
        print("Invalid choice. Please choose again.")


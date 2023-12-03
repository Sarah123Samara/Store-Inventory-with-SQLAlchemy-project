from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import csv
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")


Base = declarative_base()


class Product(Base):
    __tablename__ = "products"
    product_id = Column(Integer, primary_key=True)
    product_name = Column(String, nullable=False)
    product_quantity = Column(Integer, nullable=False)
    product_price = Column(Integer, nullable=False)
    date_updated = Column(
        Date, default=datetime.now
    )  # Use a callable for default value


# Your database URL
DATABASE_URL = "sqlite:///inventory.db"
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)


def initialize_database():
    # Initialize SQLite database
    Base.metadata.create_all(engine)


def read_csv():
    products = []
    with open("inventory.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Process and clean up the data
            row["product_quantity"] = int(row["product_quantity"])
            row["product_price"] = int(
                round(float(row["product_price"].replace("$", "")) * 100)
            )

            # Adjust the date format
            row["date_updated"] = datetime.strptime(
                row["date_updated"], "%m/%d/%Y"
            ).date()

            products.append(row)
    return products


def add_products_to_db(products, session):
    for product in products:
        # Check for duplicate product names and save the most recently updated data
        existing_product = (
            session.query(Product)
            .filter_by(product_name=product["product_name"])
            .first()
        )
        if existing_product and existing_product.date_updated < product["date_updated"]:
            continue

        new_product = Product(**product)
        session.add(new_product)
    session.commit()


# Function to display product by ID
def display_product_by_id(session):
    while True:
        id_to_search = input(
            "Enter the product ID to search (press enter to go back to menu): "
        )

        if not id_to_search:
            return  # If the user presses enter, return to the menu

        try:
            # Attempt to convert the input to an integer
            product_id = int(id_to_search)
        except ValueError:
            print("Invalid input. Please enter a valid product ID.")
            continue  # Continue to the next iteration of the loop

        product = session.query(Product).filter_by(product_id=product_id).first()

        if product:
            print("Product found with matching ID:")
            print(
                f"ID: {product.product_id}  Name: {product.product_name}  Quantity: {product.product_quantity}  Price: ${product.product_price / 100:.2f}  Date Updated: {product.date_updated}"
            )
            break  # Exit the loop if a product is found
        else:
            print(
                f"No matching product with ID '{product_id}' found. Please try again."
            )


# Function to clean date input
def clean_date(date_str):
    try:
        # Attempt to parse the date with multiple formats
        date_formats = ["%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"]
        for format_str in date_formats:
            try:
                return datetime.strptime(date_str, format_str).date()
            except ValueError:
                pass  # Continue to the next format if the current one fails

        # If none of the formats match, return None
        return None
    except ValueError:
        return None


# Function to clean price input
def clean_price(price_str):
    try:
        return float(price_str)
    except ValueError:
        return None


def add_product(session):
    while True:
        product_name = input(
            "Enter the product name (press Enter to go back to the menu): "
        ).strip()
        if not product_name:
            print("Returning to the menu.")
            return

        # Handling date input with proper error message
        while True:
            date_str = input("Enter the entry date (e.g., January 1, 2022): ").strip()
            date = clean_date(date_str)
            if date is not None:
                break
            else:
                print("Invalid date format. Please try again.")

        # Handling price input with proper error message
        while True:
            try:
                price_str = input("Enter the price (e.g., 3.19): ").strip()
                price = clean_price(price_str)
                if price is not None:
                    # Convert dollars to cents (integer)
                    price = int(round(price * 100))
                    break
                else:
                    print("Invalid price format. Please try again.")
            except ValueError:
                print("Invalid price format. Please enter a valid number.")

        # Handling quantity input with proper error message
        while True:
            try:
                product_quantity = int(input("Enter the product quantity: ").strip())
                if product_quantity >= 0:
                    break
                else:
                    print("Quantity must be a non-negative integer. Please try again.")
            except ValueError:
                print("Invalid quantity format. Please enter a valid number.")

        print("\nPlease review the information:")
        print(f"\nName: {product_name}")
        print(f"\nEntry Date: {date.strftime('%B %d, %Y')}")
        print(f"\nPrice: ${price / 100:.2f}")  # Display price in dollars
        print(f"\nQuantity: {product_quantity}")

        while True:
            print()
            confirmation = (
                input(
                    "Are you sure you have filled in the information correctly? (Yes/No) (press Enter to go back to the menu): "
                )
                .strip()
                .lower()
            )

            if confirmation == "":  # If the user pressed Enter
                print("Returning to the menu.")
                return

            if confirmation == "yes":
                # Check if a product with the same name already exists
                existing_product = (
                    session.query(Product).filter_by(product_name=product_name).first()
                )

                if existing_product:
                    # Merge the existing product with the provided information
                    existing_product.product_quantity = product_quantity
                    existing_product.product_price = price
                    existing_product.date_updated = datetime.utcnow()
                    session.merge(existing_product)
                    session.commit()
                    print(f"Updated existing product: {existing_product.product_name}")
                else:
                    # Create a new product with the provided information
                    new_product = Product(
                        product_name=product_name,
                        product_quantity=product_quantity,
                        product_price=price,
                        date_updated=datetime.utcnow(),
                    )
                    session.add(new_product)
                    session.commit()
                    print("Product added successfully!")
                return
            elif confirmation == "no":
                print("Please fill in the information again.\n")
                break
            else:
                print("Invalid input. Please enter either 'Yes' or 'No'.\n")


def backup_database(session):
    header = [
        "product_id",
        "product_name",
        "product_quantity",
        "product_price",
        "date_updated",
    ]

    # Create a set to keep track of unique products based on all information
    unique_products = set()

    products = session.query(Product).all()

    for product in products:
        # Convert product information to a tuple and add to the set
        product_info = (
            product.product_name,
            product.product_quantity,
            product.product_price,
            product.date_updated,
        )

        if product_info not in unique_products:
            unique_products.add(product_info)

    # Write the data to the backup CSV file
    with open("backup.csv", "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header)
        writer.writeheader()

        for product_info in unique_products:
            product_name, product_quantity, product_price, date_updated = product_info
            writer.writerow(
                {
                    "product_id": None,  # Assuming product_id is not relevant for backup
                    "product_name": product_name,
                    "product_quantity": product_quantity,
                    "product_price": product_price,
                    "date_updated": date_updated.strftime("%Y-%m-%d"),
                }
            )


def menu(session):
    while True:
        print("Menu:")
        print("v - View product details by ID")
        print("a - Add a new product")
        print("b - Backup the database")
        print("q - Exit")
        choice = input("Enter your choice: ").lower()

        if choice == "v":
            display_product_by_id(session)
        elif choice == "a":
            add_product(session)
        elif choice == "b":
            backup_database(session)
        elif choice == "q":
            print("Have a nice day")
            break
        else:
            print("Invalid choice. Please enter v, a, or b.")


def main():
    initialize_database()
    Session = sessionmaker(bind=engine)
    session = Session()
    products = read_csv()
    add_products_to_db(products, session)
    menu(session)
    session.close()  # Close the session when done


if __name__ == "__main__":
    main()

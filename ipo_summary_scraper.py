"""
IPO Summary Data Scraper
This script fetches year-wise IPO summary data from investorgain.com API
and saves it to the database with proper status classification.
"""


import requests
import json
import re
from datetime import datetime
from typing import Dict, List, Optional
import logging
from database.db_manager import DatabaseManager


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IPOSummaryDatabaseManager(DatabaseManager):
    """Extended Database Manager for IPO Summary data"""
    
    def create_ipo_summary_table(self):
        """Creates the IPO summary table if it doesn't exist"""
        if not self.conn:
            logger.error("Database not connected. Cannot create table.")
            return

        # Define table schema
        if self.use_sql_server:
            create_table_sql = """
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='ipo_summary_data' and xtype='U')
            CREATE TABLE ipo_summary_data (
                id INT IDENTITY(1,1) PRIMARY KEY,
                year INT NOT NULL,
                ipo_id NVARCHAR(50) NOT NULL,
                ipo_name NVARCHAR(255) NOT NULL,
                status NVARCHAR(50),
                list_price DECIMAL(15,2),
                list_gain NVARCHAR(20),
                ipo_size NVARCHAR(50),
                pe_ratio NVARCHAR(20),
                ipo_price NVARCHAR(20),
                lot_size NVARCHAR(20),
                open_date DATE,
                close_date DATE,
                boa_date DATE,
                listing_date DATE,
                url_rewrite NVARCHAR(255),
                display_order INT,
                highlight_row NVARCHAR(255),
                ipo_category NVARCHAR(50),
                rating NVARCHAR(500),
                raw_data NVARCHAR(MAX),
                created_at DATETIME DEFAULT GETDATE(),
                updated_at DATETIME DEFAULT GETDATE(),
                CONSTRAINT unique_ipo_year UNIQUE (ipo_id, year)
            );
            CREATE INDEX idx_year ON ipo_summary_data(year);
            CREATE INDEX idx_ipo_name ON ipo_summary_data(ipo_name);
            CREATE INDEX idx_created_at ON ipo_summary_data(created_at);
            """
        else:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS ipo_summary_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                ipo_id TEXT NOT NULL,
                ipo_name TEXT NOT NULL,
                status TEXT,
                list_price REAL,
                list_gain TEXT,
                ipo_size TEXT,
                pe_ratio TEXT,
                ipo_price TEXT,
                lot_size TEXT,
                open_date TEXT,
                close_date TEXT,
                boa_date TEXT,
                listing_date TEXT,
                url_rewrite TEXT,
                display_order INTEGER,
                highlight_row TEXT,
                ipo_category TEXT,
                rating TEXT,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ipo_id, year)
            );
            CREATE INDEX IF NOT EXISTS idx_year ON ipo_summary_data(year);
            CREATE INDEX IF NOT EXISTS idx_ipo_name ON ipo_summary_data(ipo_name);
            CREATE INDEX IF NOT EXISTS idx_created_at ON ipo_summary_data(created_at);
            """

        try:
            # For SQL Server, execute each statement separately
            if self.use_sql_server:
                statements = create_table_sql.split(';')
                for stmt in statements:
                    if stmt.strip():
                        self.cursor.execute(stmt)
            else:
                # For SQLite, execute all at once
                self.cursor.executescript(create_table_sql)
            
            self.conn.commit()
            logger.info("Table 'ipo_summary_data' created successfully or already exists.")
        except Exception as e:
            logger.error(f"Error creating table: {e}")

    def insert_or_update_ipo_summary(self, ipo_data: Dict) -> bool:
        """Insert or update IPO summary data"""
        if not self.conn:
            logger.error("Database not connected. Cannot insert/update data.")
            return False

        # Get required fields
        ipo_id = ipo_data.get('ipo_id')
        year = ipo_data.get('year')
        
        if not ipo_id or not year:
            logger.error("Missing required fields: ipo_id or year")
            return False

        try:
            # Check if record exists
            self.cursor.execute(
                "SELECT id FROM ipo_summary_data WHERE ipo_id = ? AND year = ?", 
                (ipo_id, year)
            )
            existing_record = self.cursor.fetchone()

            if existing_record:
                # Update existing record
                update_sql = """
                UPDATE ipo_summary_data SET 
                    ipo_name = ?, status = ?, list_price = ?, list_gain = ?, 
                    ipo_size = ?, pe_ratio = ?, ipo_price = ?, lot_size = ?,
                    open_date = ?, close_date = ?, boa_date = ?, listing_date = ?,
                    url_rewrite = ?, display_order = ?, highlight_row = ?, 
                    ipo_category = ?, rating = ?, raw_data = ?, updated_at = ?
                WHERE ipo_id = ? AND year = ?
                """
                
                update_values = [
                    ipo_data.get('ipo_name'),
                    ipo_data.get('status'),
                    ipo_data.get('list_price'),
                    ipo_data.get('list_gain'),
                    ipo_data.get('ipo_size'),
                    ipo_data.get('pe_ratio'),
                    ipo_data.get('ipo_price'),
                    ipo_data.get('lot_size'),
                    ipo_data.get('open_date'),
                    ipo_data.get('close_date'),
                    ipo_data.get('boa_date'),
                    ipo_data.get('listing_date'),
                    ipo_data.get('url_rewrite'),
                    ipo_data.get('display_order'),
                    ipo_data.get('highlight_row'),
                    ipo_data.get('ipo_category'),
                    ipo_data.get('rating'),
                    ipo_data.get('raw_data'),
                    datetime.now().isoformat() if not self.use_sql_server else datetime.now(),
                    ipo_id,
                    year
                ]
                
                self.cursor.execute(update_sql, update_values)
                logger.info(f"Updated IPO ID: {ipo_id} for year {year}")
            else:
                # Insert new record
                insert_sql = """
                INSERT INTO ipo_summary_data (
                    year, ipo_id, ipo_name, status, list_price, list_gain,
                    ipo_size, pe_ratio, ipo_price, lot_size, open_date, 
                    close_date, boa_date, listing_date, url_rewrite, 
                    display_order, highlight_row, ipo_category, rating, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                insert_values = [
                    year,
                    ipo_id,
                    ipo_data.get('ipo_name'),
                    ipo_data.get('status'),
                    ipo_data.get('list_price'),
                    ipo_data.get('list_gain'),
                    ipo_data.get('ipo_size'),
                    ipo_data.get('pe_ratio'),
                    ipo_data.get('ipo_price'),
                    ipo_data.get('lot_size'),
                    ipo_data.get('open_date'),
                    ipo_data.get('close_date'),
                    ipo_data.get('boa_date'),
                    ipo_data.get('listing_date'),
                    ipo_data.get('url_rewrite'),
                    ipo_data.get('display_order'),
                    ipo_data.get('highlight_row'),
                    ipo_data.get('ipo_category'),
                    ipo_data.get('rating'),
                    ipo_data.get('raw_data')
                ]
                
                self.cursor.execute(insert_sql, insert_values)
                logger.info(f"Inserted new IPO ID: {ipo_id} for year {year}")

            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error inserting/updating IPO summary data: {e}")
            self.conn.rollback()
            return False


class IPOSummaryScraper:
    """Scraper for IPO summary data from investorgain.com"""
    
    def __init__(self):
        self.base_url_template = "https://webnodejs.investorgain.com/cloud/report/data-read/394/1/{month}/{year}/2025-26/0/all"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Referer": "https://www.investorgain.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }
        self.db_manager = IPOSummaryDatabaseManager()
        
    def extract_status_info(self, status_html: str) -> Dict[str, Optional[str]]:
        """Extract status, list price, and list gain from status HTML"""
        status_info = {
            'status': None,
            'list_price': None,
            'list_gain': None
        }
        
        if not status_html:
            return status_info
            
        # Clean HTML and extract text
        clean_status = re.sub(r'<[^>]+>', '', status_html).strip()
        
        # Determine status
        if 'Upcoming' in status_html:
            status_info['status'] = 'Upcoming'
        elif 'Open' in status_html:
            status_info['status'] = 'Open'
        elif 'Closing Today' in status_html:
            status_info['status'] = 'Closing Today'
        elif 'Close' in status_html:
            status_info['status'] = 'Close'
        elif 'L@' in status_html:
            status_info['status'] = 'Listed'
            
            # Extract listing price and gain
            # Pattern: L@2500 (66.33%)
            listing_pattern = r'L@([\d.]+)\s*\(([^)]+)\)'
            match = re.search(listing_pattern, clean_status)
            if match:
                status_info['list_price'] = float(match.group(1))
                status_info['list_gain'] = match.group(2).strip()
        
        return status_info
    
    def parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to standard format YYYY-MM-DD"""
        if not date_str or date_str.strip() == '':
            return None
            
        try:
            # Handle formats like "3-Jul-25", "21-Oct-24"
            if '-' in date_str:
                parts = date_str.split('-')
                if len(parts) == 3:
                    day = parts[0].zfill(2)
                    month_str = parts[1]
                    year = parts[2]
                    
                    # Convert year to full year
                    if len(year) == 2:
                        year = '20' + year if int(year) < 50 else '19' + year
                    
                    # Convert month name to number
                    months = {
                        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                        'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                        'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                    }
                    
                    month = months.get(month_str, '01')
                    return f"{year}-{month}-{day}"
            
            return None
        except Exception as e:
            logger.warning(f"Error parsing date '{date_str}': {e}")
            return None
    
    def clean_text(self, text: str) -> str:
        """Clean text by removing HTML entities and extra whitespace"""
        if not text:
            return ""
        
        # Replace HTML entities first
        text = text.replace('&#8377;', '₹')  # Replace HTML currency entity with rupee symbol
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        
        # Remove Unicode currency symbols for cleaner data storage
        text = text.replace('\u20b9', '')  # Remove Unicode rupee symbol
        text = text.replace('₹', '')  # Remove rupee symbol
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def process_ipo_record(self, record: Dict, year: int) -> Dict:
        """Process a single IPO record from API response"""
        # Extract status information
        status_info = self.extract_status_info(record.get('Status', ''))
        
        # Process the record
        processed_record = {
            'year': year,
            'ipo_id': str(record.get('~id', '')),
            'ipo_name': self.clean_text(record.get('IPO', '')),
            'status': status_info['status'],
            'list_price': status_info['list_price'],
            'list_gain': status_info['list_gain'],
            'ipo_size': self.clean_text(record.get('IPO Size', '')),
            'pe_ratio': self.clean_text(record.get('P/E', '')),
            'ipo_price': self.clean_text(record.get('IPO Price', '')),
            'lot_size': self.clean_text(record.get('Lot', '')),
            'open_date': self.parse_date(record.get('Open', '')),
            'close_date': self.parse_date(record.get('Close', '')),
            'boa_date': self.parse_date(record.get('BoA Dt', '')),
            'listing_date': self.parse_date(record.get('Listing', '')),
            'url_rewrite': record.get('~URLRewrite_Folder_Name', ''),
            'display_order': record.get('~Display_Order'),
            'highlight_row': record.get('~Highlight_Row', ''),
            'ipo_category': record.get('~IPO_Category', ''),
            'rating': self.clean_text(record.get('~Rating', '')),
            'raw_data': json.dumps(record, ensure_ascii=False)
        }
        
        return processed_record
    
    def fetch_year_data(self, year: int) -> List[Dict]:
        """Fetch IPO data for a specific year, using current month dynamically"""
        current_month = datetime.now().month  # Gets the current month (e.g., 8 for August)
        url = self.base_url_template.format(month=current_month, year=year)
        
        # Optionally add query params if needed (e.g., for filtering), but keeping it minimal as per your example
        url += "?search="  # Empty search; add &v= if tests show it's required for some years
        
        try:
            logger.info(f"Fetching data for year {year} (using month {current_month}) from: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check if response has the expected structure
            if isinstance(data, dict) and 'reportTableData' in data:
                records = data['reportTableData']
                total_records = data.get('totalRecords', len(records))
                logger.info(f"Found {len(records)} IPO records for year {year} (total: {total_records})")
                return records
            elif isinstance(data, list):
                logger.info(f"Found {len(data)} IPO records for year {year}")
                return data
            else:
                logger.warning(f"Unexpected response format for year {year}: {type(data)}")
                logger.warning(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data for year {year}: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON for year {year}: {e}")
            return []
    
    def scrape_year(self, year: int) -> int:
        """Scrape and save IPO data for a specific year"""
        logger.info(f"Starting scrape for year {year}")
        
        # Connect to database if not already connected
        if not self.db_manager.conn:
            self.db_manager.connect()
            if not self.db_manager.conn:
                logger.error("Failed to connect to database")
                return 0
            
            # Create table if it doesn't exist
            self.db_manager.create_ipo_summary_table()
        
        # Fetch data
        raw_data = self.fetch_year_data(year)
        if not raw_data:
            logger.warning(f"No data found for year {year}")
            return 0
        
        # Process and save data
        saved_count = 0
        for record in raw_data:
            try:
                processed_record = self.process_ipo_record(record, year)
                
                # Skip if essential data is missing
                if not processed_record['ipo_id'] or not processed_record['ipo_name']:
                    logger.warning(f"Skipping record with missing essential data: {record}")
                    continue
                
                # Save to database
                if self.db_manager.insert_or_update_ipo_summary(processed_record):
                    saved_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing record for year {year}: {e}")
                logger.debug(f"Problematic record: {record}")
        
        logger.info(f"Saved {saved_count} records for year {year}")
        return saved_count
    
    def close(self):
        """Close database connection"""
        if self.db_manager:
            self.db_manager.close()
    
    def scrape_all_years(self, years: List[int] = None) -> Dict[int, int]:
        """Scrape IPO data for all specified years"""
        if years is None:
            years = [2025, 2024, 2023, 2022, 2021, 2020, 2019]
        
        # Connect to database
        self.db_manager.connect()
        if not self.db_manager.conn:
            logger.error("Failed to connect to database")
            return {}
        
        # Create table if it doesn't exist
        self.db_manager.create_ipo_summary_table()
        
        results = {}
        total_saved = 0
        
        try:
            for year in years:
                saved_count = self.scrape_year(year)
                results[year] = saved_count
                total_saved += saved_count
                
                logger.info(f"Completed year {year}: {saved_count} records saved")
        
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        
        finally:
            self.db_manager.close()
        
        logger.info(f"Scraping completed. Total records saved: {total_saved}")
        logger.info(f"Results by year: {results}")
        
        return results


def main():
    """Main function to run the IPO summary scraper"""
    logger.info("Starting IPO Summary Data Scraper")
    
    scraper = IPOSummaryScraper()
    
    # Define years to scrape
    years_to_scrape = [2025, 2024, 2023, 2022, 2021, 2020, 2019]
    
    # Run the scraper
    results = scraper.scrape_all_years(years_to_scrape)
    
    # Print summary
    print("\n" + "="*50)
    print("IPO SUMMARY SCRAPING RESULTS")
    print("="*50)
    
    total_records = 0
    for year, count in results.items():
        print(f"Year {year}: {count} records saved")
        total_records += count
    
    print(f"\nTotal records saved: {total_records}")
    print("="*50)
    
    logger.info("IPO Summary Data Scraper completed successfully")


if __name__ == "__main__":
    main()

import os
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side

class ExcelRoutingEngine:
    def __init__(self, template_path="database/templates/2. Order form V7.xlsx", output_dir="output", debug_mode=False):
        self.debug_mode = debug_mode
        self.template_path = template_path
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_excel(self, verified_session_data):
        client_name = verified_session_data.get("client_name", "Unknown Client")
        project_po = verified_session_data.get("project_po", "Unknown PO")
        items = verified_session_data.get("products", [])

        if not os.path.exists(self.template_path):
            print(f"Error: Template not found at {self.template_path}")
            return None

        # Load Template
        wb = openpyxl.load_workbook(self.template_path)
        base_sheet = wb.active
        base_sheet.title = "__TEMPLATE__" # Temporary name

        from collections import defaultdict
        rooms = defaultdict(list)
        for item in items:
            rooms[item.get("room", "General")].append(item)

        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                             top=Side(style='thin'), bottom=Side(style='thin'))

        for room_idx, (room_name, room_products) in enumerate(rooms.items()):
            # Create a true duplicate of the base sheet to retain all formatting
            sheet = wb.copy_worksheet(base_sheet)
            sheet.title = f"Tab {room_idx+1} - {room_name}"

            # Inject Headers
            sheet.cell(row=2, column=4, value=f"Costumer: {client_name}")
            sheet.cell(row=3, column=4, value=f"PO #: {project_po}")

            # Find insertion point
            start_row = 6
            while sheet.cell(row=start_row, column=4).value is not None:
                start_row += 1

            for item in room_products:
                routing_tag = item.get("routing_tag", "Standard")
                dims = item.get("dimensions", {})
                dim_str = "x".join(str(v) for v in dims.values()) if dims else ""

                row_data = {
                    3: routing_tag,                   # C: Line Costing
                    4: item.get("type", ""),          # D: Item
                    5: item.get("description", ""),   # E: Description
                    6: item.get("finish", ""),        # F: Color/Finish
                    7: dim_str,                       # G: Size
                    8: item.get("sku", item.get("id", "")), # H: Item code
                    9: item.get("brand", ""),         # I: Brand
                    10: item.get("provider", ""),     # J: Supplier
                    11: item.get("qty", 1),           # K: Qty
                    12: item.get("purchase_link", "") # L: Purchase Link / Action
                }

                for col_idx, value in row_data.items():
                    cell = sheet.cell(row=start_row, column=col_idx, value=value)
                    cell.border = thin_border
                    
                    # Apply hyperlink styling if column L is a true URL
                    if col_idx == 12 and isinstance(value, str):
                        if value.startswith("http://") or value.startswith("https://"):
                            cell.hyperlink = value
                            cell.font = Font(color="0000FF", underline="single")
                    
                start_row += 1

        # Remove the pristine template sheet before saving
        wb.remove(base_sheet)

        output_path = os.path.join(self.output_dir, f"{client_name.replace(' ', '_')}_{project_po}_Materials_Cart.xlsx")
        wb.save(output_path)
        print(f"✅ Multi-tab Excel generated at: {output_path}")
        return output_path

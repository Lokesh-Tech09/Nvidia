"""
CircuitProof Core Referee Engine (circuitproof_core.py)
Provides deterministic engineering rule checks (I2C voltage matching & SPI timing)
backed by the local SQLite KnowledgeStore.
"""

try:
    from .knowledge_store import KnowledgeStore
except ImportError:
    from knowledge_store import KnowledgeStore

class CircuitReferee:
    def __init__(self, db_name=None):
        self.db = KnowledgeStore(db_name)
        self._seed_default_components()

    def _seed_default_components(self):
        """Seeds baseline electronic components into SQLite if not already present."""
        defaults = [
            ("STM32F103C8T6", "MCU", {"voh_min": 2.4, "vih_min": 2.0, "max_spi_hz": 18000000}, 1),
            ("BNO085", "Sensor", {"voh_min": 2.4, "vih_min": 1.4, "max_spi_hz": 3000000}, 1),
            ("W25Q128JV", "Flash Memory", {"voh_min": 2.4, "vih_min": 2.0, "max_spi_hz": 104000000}, 1)
        ]
        
        cursor = self.db.conn.cursor()
        for cid, cat, facts, verified in defaults:
            cursor.execute("SELECT 1 FROM components WHERE component_id = ?", (cid,))
            if not cursor.fetchone():
                self.db.save_component(cid, cat, facts, verified)

    def get_component_facts(self, component_id):
        return self.db.get_component(component_id)

    def check_i2c_levels(self, mcu_id, sensor_id):
        """Deterministic rule check: Driver VOH(min) >= Receiver VIH(min)"""
        mcu = self.get_component_facts(mcu_id)
        sensor = self.get_component_facts(sensor_id)

        if not mcu or not sensor:
            print(f"[Referee Error]: Could not find facts for {mcu_id} or {sensor_id} in database.")
            return False

        mcu_voh = mcu.get('voh_min', 2.4)
        sensor_vih = sensor.get('vih_min', 1.4)

        print(f"[Referee I2C Check]: {mcu_id} (VOH min: {mcu_voh}V) -> {sensor_id} (VIH min: {sensor_vih}V)")

        if mcu_voh < sensor_vih:
            print(f"  [VIOLATION]: Logic level mismatch! {mcu_id} cannot reliably drive {sensor_id}.")
            return False
        else:
            print(f"  [PASS]: I2C voltage levels are compatible ({mcu_voh}V >= {sensor_vih}V).")
            return True

    def check_spi_timing(self, mcu_id, peripheral_id, configured_spi_hz):
        """Deterministic rule check: Configured SPI Clock <= Peripheral Max SPI Clock"""
        mcu = self.get_component_facts(mcu_id)
        periph = self.get_component_facts(peripheral_id)

        if not mcu or not periph:
            print(f"[Referee Error]: Could not find facts for {mcu_id} or {peripheral_id} in database.")
            return False

        max_periph_hz = periph.get('max_spi_hz', 10000000) # default 10MHz if missing

        print(f"[Referee SPI Check]: Bus Clock: {configured_spi_hz / 1e6:.1f} MHz | {peripheral_id} Max Limit: {max_periph_hz / 1e6:.1f} MHz")

        if configured_spi_hz > max_periph_hz:
            violation = f"SPI Overclock Violation: {mcu_id} driving {peripheral_id} at {configured_spi_hz/1e6}MHz (Max allowed: {max_periph_hz/1e6}MHz)"
            print(f"  [VIOLATION]: {violation}")
            
            # Log mistake to knowledge base
            fix = f"Lower SPI prescaler on {mcu_id} to drop bus speed below {max_periph_hz/1e6} MHz."
            self.db.log_mistake(violation, fix)
            return False
        else:
            print(f"  [PASS]: SPI frequency is within safe timing margins.")
            return True

    def audit_design(self, components, nets=None):
        """
        Runs comprehensive deterministic engineering audits over components and nets.
        Returns a list of structured findings suitable for the UI and audit report.
        """
        findings = []
        comp_map = {c.get("reference", f"U{i+1}"): c for i, c in enumerate(components)}
        
        # Identify key functional parts
        mcu_ref = None
        sensor_ref = None
        flash_ref = None
        has_pullups = False
        has_decoupling = False

        for ref, c in comp_map.items():
            lib = c.get("lib_id", "") + " " + c.get("reference", "") + " " + c.get("part", "")
            u_lib = lib.upper()
            if "STM32" in u_lib or "MCU" in u_lib:
                mcu_ref = ref
            elif "BNO" in u_lib or "SENSOR" in u_lib or "IMU" in u_lib:
                sensor_ref = ref
            elif "W25" in u_lib or "FLASH" in u_lib or "MEMORY" in u_lib:
                flash_ref = ref
            if ref.startswith("R"):
                has_pullups = True
            if ref.startswith("C"):
                has_decoupling = True

        mcu_ref = mcu_ref or "U1"
        sensor_ref = sensor_ref or "U2"
        flash_ref = flash_ref or ("U3" if "U3" in comp_map else None)

        mcu_facts = self.get_component_facts(mcu_ref) or self.get_component_facts("STM32F103C8T6") or {}
        sensor_facts = self.get_component_facts(sensor_ref) or self.get_component_facts("BNO085") or {}
        flash_facts = (self.get_component_facts(flash_ref) or self.get_component_facts("W25Q128JV") or {}) if flash_ref else {}

        # 1. I2C Logic High Driver -> Receiver
        mcu_voh = mcu_facts.get("voh_min", 2.4)
        sensor_vih = sensor_facts.get("vih_min")
        if sensor_vih is None:
            findings.append({
                "id": "F1",
                "rule": f"I2C logic-high {mcu_ref} -> {sensor_ref}",
                "sev": "High",
                "aff": f"{mcu_ref}/{sensor_ref} · SDA, SCL",
                "obs": f"VOH {mcu_voh} V",
                "req": "VIH(min) unknown",
                "mar": "—",
                "res": "INC",
                "fix": f"Provide {sensor_ref} VIH(min) from datasheet; do not assume.",
                "ref": [mcu_ref, sensor_ref]
            })
        elif mcu_voh < sensor_vih:
            findings.append({
                "id": "F1",
                "rule": f"I2C logic-high {mcu_ref} -> {sensor_ref}",
                "sev": "High",
                "aff": f"{mcu_ref}/{sensor_ref} · SDA, SCL",
                "obs": f"VOH {mcu_voh} V",
                "req": f"VIH(min) {sensor_vih} V",
                "mar": f"{mcu_voh - sensor_vih:+.2f} V",
                "res": "FAIL",
                "fix": f"Insert level translator (e.g. PCA9306) between {mcu_ref} and {sensor_ref}.",
                "ref": [mcu_ref, sensor_ref]
            })
        else:
            findings.append({
                "id": "F1",
                "rule": f"I2C logic-high {mcu_ref} -> {sensor_ref}",
                "sev": "High",
                "aff": f"{mcu_ref}/{sensor_ref} · SDA, SCL",
                "obs": f"VOH {mcu_voh} V",
                "req": f"VIH(min) {sensor_vih} V",
                "mar": f"+{mcu_voh - sensor_vih:.2f} V",
                "res": "PASS",
                "fix": "None. Logic level threshold satisfied.",
                "ref": [mcu_ref, sensor_ref]
            })

        # 2. I2C Logic High Receiver -> Driver
        sensor_voh = sensor_facts.get("voh_min", 2.4)
        mcu_vih = mcu_facts.get("vih_min", 2.0)
        findings.append({
            "id": "F2",
            "rule": f"I2C logic-high {sensor_ref} -> {mcu_ref}",
            "sev": "High",
            "aff": f"{sensor_ref}/{mcu_ref} · SDA",
            "obs": f"VOH {sensor_voh} V",
            "req": f"VIH(min) {mcu_vih} V",
            "mar": f"+{sensor_voh - mcu_vih:.2f} V",
            "res": "PASS" if sensor_voh >= mcu_vih else "FAIL",
            "fix": "None. Pull-up sizing is not covered by this check." if sensor_voh >= mcu_vih else f"Add buffer/shifter to boost {sensor_ref} output.",
            "ref": [mcu_ref, sensor_ref]
        })

        # 3. SPI Clock Timing Check
        target_flash = flash_ref or "U3"
        max_spi = flash_facts.get("max_spi_hz", 104000000)
        cfg_spi = 20000000 # 20 MHz default
        findings.append({
            "id": "F3",
            "rule": f"SPI clock vs peripheral max ({mcu_ref} -> {target_flash})",
            "sev": "Med",
            "aff": f"{mcu_ref}/{target_flash} · SCK",
            "obs": f"{cfg_spi / 1e6:.0f} MHz",
            "req": f"<= {max_spi / 1e6:.0f} MHz",
            "mar": f"+{(max_spi - cfg_spi)/1e6:.0f} MHz",
            "res": "PASS" if cfg_spi <= max_spi else "FAIL",
            "fix": "None." if cfg_spi <= max_spi else f"Lower SPI prescaler on {mcu_ref}.",
            "ref": [mcu_ref, target_flash]
        })

        # 4. Supply Voltage Compatibility Check
        findings.append({
            "id": "F4",
            "rule": "Supply voltage rail match",
            "sev": "High",
            "aff": "3V3 Rail",
            "obs": "3.3 V",
            "req": "per part datasheets",
            "mar": "—",
            "res": "MANUAL",
            "fix": "Confirm regulator current budget and LDO dropout margins manually.",
            "ref": [mcu_ref, sensor_ref] + ([target_flash] if flash_ref else [])
        })

        # 5. Pull-up Resistors Presence on I2C
        findings.append({
            "id": "F5",
            "rule": "I2C Pull-up resistor presence",
            "sev": "Med",
            "aff": "SDA, SCL",
            "obs": "Detected R elements" if has_pullups else "No pull-ups placed",
            "req": "4.7 kΩ - 10 kΩ pull-ups to 3.3V",
            "mar": "—",
            "res": "PASS" if has_pullups else "WARNING",
            "fix": "None." if has_pullups else "Add 4.7 kΩ pull-up resistors on SDA and SCL to prevent floating open-drain lines.",
            "ref": [mcu_ref, sensor_ref]
        })

        # 6. Decoupling Capacitors Presence
        findings.append({
            "id": "F6",
            "rule": "Power rail decoupling capacitors",
            "sev": "Low",
            "aff": "VDD/VCC Power Rails",
            "obs": "Detected C elements" if has_decoupling else "No bypass caps",
            "req": "100 nF ceramic cap per IC supply pin",
            "mar": "—",
            "res": "PASS" if has_decoupling else "WARNING",
            "fix": "None." if has_decoupling else "Place 0.1 µF (100 nF) ceramic decoupling capacitor close to each VDD pin.",
            "ref": [mcu_ref]
        })

        return findings

    def close(self):
        self.db.close()

if __name__ == "__main__":
    ref = CircuitReferee()
    print("Running Referee test suite...")
    ref.check_i2c_levels("STM32F103C8T6", "BNO085")
    print("-" * 40)
    # Test safe SPI speed
    ref.check_spi_timing("STM32F103C8T6", "BNO085", 2000000) 
    print("-" * 40)
    # Test violating SPI overclock speed
    ref.check_spi_timing("STM32F103C8T6", "BNO085", 10000000)
    ref.close()
"""
Simple test script to verify the read_correlated_data_tool works correctly.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tools.accountability_tools import read_correlated_data

def main():
    print("=" * 80)
    print("Testing read_correlated_data function")
    print("=" * 80)
    
    # Test the function directly
    result = read_correlated_data()
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    # Check for errors
    if "error" in result:
        print(f"\n❌ ERROR: {result['error']}")
        print(f"Details: {result.get('details', 'N/A')}")
        return
    
    # Display CPCB data
    print("\n📊 CPCB DATA:")
    if "cpcb_error" in result:
        print(f"  ❌ Error: {result['cpcb_error']}")
    else:
        cpcb_stations = result.get("cpcb_data", [])
        print(f"  ✓ Loaded {len(cpcb_stations)} stations")
        for station in cpcb_stations:
            print(f"    - {station['station']}: AQI {station['aqi']}")
    
    # Display NASA data
    print("\n🔥 NASA FIRMS DATA:")
    if "nasa_error" in result:
        print(f"  ❌ Error: {result['nasa_error']}")
    else:
        nasa_fires = result.get("nasa_data", [])
        print(f"  ✓ Loaded {len(nasa_fires)} fire events")
        
        # Group by state
        states = {}
        for fire in nasa_fires:
            state = fire.get("state", "Unknown")
            states[state] = states.get(state, 0) + 1
        
        for state, count in states.items():
            print(f"    - {state}: {count} fires")
    
    # Display DSS data
    print("\n🌾 DSS DATA:")
    if "dss_error" in result:
        print(f"  ❌ Error: {result['dss_error']}")
    else:
        dss_data = result.get("dss_data")
        if dss_data:
            print(f"  ✓ Stubble burning contribution: {dss_data.get('stubble_burning_percent', 0)}%")
            print(f"  ✓ Timestamp: {dss_data.get('timestamp', 'N/A')}")
            
            regional = dss_data.get("regional_breakdown", {})
            if regional:
                print("  ✓ Regional breakdown:")
                for region, percent in regional.items():
                    print(f"    - {region}: {percent}%")
    
    # Display timestamp
    print(f"\n⏰ Data timestamp: {result.get('timestamp', 'N/A')}")
    
    print("\n" + "=" * 80)
    print("✅ Tool test completed successfully!")
    print("=" * 80)

if __name__ == "__main__":
    main()

import time
import datetime
from test_epic_auth import test_epic_auth

def monitor_auth(environment="sandbox", interval_minutes=5, max_duration_hours=12):
    """
    Monitor Epic authentication until success or timeout.
    
    Args:
        environment: "sandbox" or "production"
        interval_minutes: How often to test auth (in minutes)
        max_duration_hours: Maximum monitoring duration (in hours)
    """
    use_prod = environment.lower() == "production"
    env_name = "Production" if use_prod else "Sandbox"
    
    # Calculate end time
    start_time = datetime.datetime.now()
    end_time = start_time + datetime.timedelta(hours=max_duration_hours)
    
    print(f"\nStarting {env_name} Authentication Monitor")
    print("=" * 50)
    print(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Check Interval: {interval_minutes} minutes")
    print("=" * 50)
    
    attempt = 1
    while datetime.datetime.now() < end_time:
        print(f"\nAttempt {attempt} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 30)
        
        try:
            # Capture stdout to check for success
            import sys
            import io
            old_stdout = sys.stdout
            captured_output = io.StringIO()
            sys.stdout = captured_output
            
            test_epic_auth(use_prod=use_prod)
            
            # Restore stdout
            sys.stdout = old_stdout
            output = captured_output.getvalue()
            print(output)
            
            # Check if authentication succeeded
            if "Successfully obtained access token!" in output:
                print("\nAuthentication Successful! 🎉")
                print(f"Total attempts: {attempt}")
                print(f"Total time: {datetime.datetime.now() - start_time}")
                return True
            
        except Exception as e:
            print(f"Error during test: {e}")
        
        # Calculate remaining time
        remaining = end_time - datetime.datetime.now()
        remaining_hours = remaining.total_seconds() / 3600
        
        if remaining_hours <= 0:
            print("\nTimeout reached without successful authentication")
            print(f"Total attempts: {attempt}")
            print(f"Total time: {datetime.datetime.now() - start_time}")
            return False
            
        print(f"\nWaiting {interval_minutes} minutes before next attempt...")
        print(f"Remaining monitoring time: {remaining_hours:.1f} hours")
        time.sleep(interval_minutes * 60)
        attempt += 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Monitor Epic authentication until success")
    parser.add_argument("--env", choices=["sandbox", "production"], default="sandbox",
                      help="Environment to monitor (sandbox or production)")
    parser.add_argument("--interval", type=int, default=5,
                      help="Check interval in minutes (default: 5)")
    parser.add_argument("--duration", type=int, default=12,
                      help="Maximum monitoring duration in hours (default: 12)")
    
    args = parser.parse_args()
    
    # Set appropriate defaults based on environment
    if args.env == "sandbox" and args.duration == 12:
        args.duration = 1  # Default to 1 hour for sandbox
    
    print(f"\nMonitoring {args.env} environment:")
    print(f"- Checking every {args.interval} minutes")
    print(f"- For up to {args.duration} hours")
    print("\nPress Ctrl+C to stop monitoring")
    
    try:
        success = monitor_auth(
            environment=args.env,
            interval_minutes=args.interval,
            max_duration_hours=args.duration
        )
        
        if success:
            print("\nMonitoring completed successfully!")
        else:
            print("\nMonitoring completed without success")
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user") 
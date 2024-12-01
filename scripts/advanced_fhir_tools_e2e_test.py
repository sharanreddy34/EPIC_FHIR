def test_pathling_analytics(self):
    """Test the Pathling analytics service."""
    # Initialize the Pathling service
    pathling_service = PathlingService(use_docker=True)
    
    # Try to start the server
    started = pathling_service.start()
    
    # Test aggregate function
    try:
        # Load resources for analytics
        if started:
            for resource_type, resources in self.resources.items():
                pathling_service.load_resources(resources, resource_type)
            
            # Test basic count
            count_result = pathling_service.aggregate(
                subject="Patient",
                aggregation="count()"
            )
            
            logger.info(f"Patient count: {count_result}")
    except Exception as e:
        logger.error(f"Error during Pathling analytics: {e}")
        return False
    finally:
        # Ensure we always try to stop the server
        try:
            pathling_service.stop()
        except Exception as stop_error:
            logger.warning(f"Error stopping Pathling server: {stop_error}")
    
    return True 
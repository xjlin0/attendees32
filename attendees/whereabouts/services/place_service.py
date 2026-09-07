class PlaceService:
    @staticmethod
    def destroy_with_associations(place):
        """
        Delete the place. Also delete its associated address if no active place is using it.
        """
        address = place.address
        place.delete()
        
        if address and address.place.count() == 0:
            address.delete()

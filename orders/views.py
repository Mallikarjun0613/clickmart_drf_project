from django.shortcuts import render,get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from carts.models import Cart, CartItem
from rest_framework.response import Response
from .models import Order, OrderItem
from .serializers import OrderSerializer
from rest_framework import status
from .utils import send_order_notification
from rest_framework.generics import ListAPIView,RetrieveAPIView


class PlaceOrderView(APIView):
    # the user be logged in
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # check if the cart is empty
        shipping_data = request.data.get('shippingAddress', {})
        # check if the cart is empty
        cart = Cart.objects.get(user=request.user)
        if not cart or cart.items.count() == 0:
            return Response({'error': 'Cart is empty'})

        # create the order
        order = Order.objects.create(
            user = request.user,
            phone=shipping_data.get('phone'),
            subtotal = cart.subtotal,
            tax_amount = cart.tax_amount,
            grand_total = cart.grand_total,
            address=shipping_data.get('address'),
            city=shipping_data.get('city'),
            state=shipping_data.get('state'),
            zip_code=shipping_data.get('zipCode'),

        )
        # Loop through the cart items
        for item in cart.items.all(): 
            product = item.product

    # check quantity
        if product.stock < item.quantity:
            return Response({"details": f'Only {product.stock} is left for {product.name}'}, 
                        status=status.HTTP_400_BAD_REQUEST)
        
        # Decrease the product quantity (Update)
        product.stock -= item.quantity
        product.save()

        # create order items
        for item in cart.items.all():
            OrderItem.objects.create(
                order = order,
                product = item.product,
                quantity = item.quantity,
                price = item.product.price,
                total_price = item.total_price
            )


        # clear the cart items
        cart.items.all().delete()
        cart.save()


        # send the notification email
        send_order_notification(order)
        # send the response to frontend
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    

class MyOrdersView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
    
class OrderDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_object(self):
        pk = self.kwargs.get('pk')
        order = get_object_or_404(Order, pk=pk, user=self.request.user)
        return order

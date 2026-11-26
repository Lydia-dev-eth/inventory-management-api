from django.shortcuts import render
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import LoginSerializer
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated

class LoginView(APIView):
    permission_classes = [AllowAny]
# Create your views here. 
class LoginView(APIView):
    permission_classes = [AllowAny]    
    def post(self,request):
        serializer= LoginSerializer(data=request.data)
        if serializer.is_valid():
            username=serializer.validated_data["username"]
            password=serializer.validated_data["password"]
            user = authenticate(
                username=username,
                password=password
            )
            if user is not None:
                token,created= Token.objects.get_or_create(user=user)
                return Response({
                    "token": token.key,
                    "user_id": user.id,
                    "username": user.username,
                    "role": user.role,
                })
            return Response(
                {"error": "Invalid username or password"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()

        return Response(
            {"message": "Successfully logged out."},
            status=status.HTTP_200_OK
        )





    
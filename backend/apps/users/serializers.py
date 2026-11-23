from rest_framework import serializers

from .models import Brigade, RoleCode, User, UserStatus
from .permissions import can_edit_user, manageable_user_roles


class CurrentUserSerializer(serializers.ModelSerializer):
    manageable_roles = serializers.SerializerMethodField()

    def get_manageable_roles(self, obj):
        allowed = manageable_user_roles(obj)
        return [{"value": value, "label": label} for value, label in RoleCode.choices if value in allowed]

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "status",
            "role",
            "manageable_roles",
        )


class UserAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    can_edit = serializers.SerializerMethodField()

    def get_can_edit(self, obj):
        return can_edit_user(self.context["request"].user, obj)

    def validate(self, attrs):
        actor = self.context["request"].user
        role = attrs.get("role", self.instance.role if self.instance else User._meta.get_field("role").default)
        if role not in manageable_user_roles(actor):
            raise serializers.ValidationError({"role": "Вы не можете назначить эту роль."})
        target_status = attrs.get('status', self.instance.status if self.instance else UserStatus.ACTIVE)
        if 'status' in attrs:
            attrs['is_active'] = target_status == UserStatus.ACTIVE
        elif target_status != UserStatus.ACTIVE:
            attrs['is_active'] = False
        if self.instance and attrs.get('status') == UserStatus.DISMISSED:
            from django.db.models import Q
            from apps.workday.models import WorkDay, WorkDayStatus
            if WorkDay.objects.filter(Q(foreman=self.instance) | Q(workers_present=self.instance), status=WorkDayStatus.OPEN).exists():
                raise serializers.ValidationError({'status': 'Сотрудник участвует в открытой смене. Сначала закройте смену.'})
        return attrs

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "status",
            "role",
            "is_active",
            "password",
            "can_edit",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class BrigadeSerializer(serializers.ModelSerializer):
    foreman_username = serializers.CharField(source="foreman.username", read_only=True)
    member_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=False,
        source="members",
        write_only=True,
    )
    member_usernames = serializers.SlugRelatedField(
        source="members",
        many=True,
        read_only=True,
        slug_field="username",
    )

    class Meta:
        model = Brigade
        fields = (
            "id",
            "name",
            "foreman",
            "foreman_username",
            "is_active",
            "member_ids",
            "member_usernames",
        )

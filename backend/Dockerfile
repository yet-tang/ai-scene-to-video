# Build stage
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app

ARG IMAGE_TAG=unknown
ARG GIT_COMMIT=unknown
ARG BUILD_TIME

COPY pom.xml .
COPY src ./src

# Print version info
RUN echo "=== Backend Build Info ==="
RUN echo "IMAGE_TAG: $IMAGE_TAG"
RUN echo "GIT_COMMIT: $GIT_COMMIT"
RUN echo "BUILD_TIME: $BUILD_TIME"
RUN echo "========================="

RUN mvn clean package -DskipTests

# Run stage
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

ARG IMAGE_TAG=unknown
ARG GIT_COMMIT=unknown
ARG BUILD_TIME

# Set version info as environment variables
ENV IMAGE_TAG=$IMAGE_TAG
ENV GIT_COMMIT=$GIT_COMMIT
ENV BUILD_TIME=$BUILD_TIME

COPY --from=build /app/target/*.jar app.jar
EXPOSE 8090
ENTRYPOINT ["java", "-Dimage.tag=${IMAGE_TAG}", "-Dgit.commit=${GIT_COMMIT}", "-Dbuild.time=${BUILD_TIME}", "-jar", "app.jar"]

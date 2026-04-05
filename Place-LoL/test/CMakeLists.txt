cmake_minimum_required(VERSION 3.0.2)

project(test)

install(
DIRECTORY 3D_input_default DESTINATION ${PROJECT_NAME}
)

install(
DIRECTORY 3D_input_inflated DESTINATION ${PROJECT_NAME}
)

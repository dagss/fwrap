! Run two times, one with template detection on and one without.
! Make sure that the one with templates run last, so that the result
! can be inspected in BUILD.
! configure-flags:
! configure-flags: --detect-templates

subroutine s_differ_in_number(x)
  integer :: x
end subroutine

subroutine d_differ_in_number(x, y)
  integer :: x, y
end subroutine

subroutine s_differ_in_dimension(x)
  integer :: x
end subroutine

subroutine d_differ_in_dimension(x)
  integer, dimension(:) :: x
end subroutine


subroutine gfoo(n, b, c)
  integer, intent(in) :: n
  double precision, intent(inout), dimension(n) :: b
  double precision, intent(out), dimension(n) :: c
  c = b
end subroutine

subroutine sfoo(n, b, c)
  integer, intent(in) :: n
  real, intent(inout), dimension(n) :: b
  real, intent(out), dimension(n) :: c
  b = b * 1
  c = b
end subroutine

subroutine dfoo(n, b, c)
  integer, intent(in) :: n
  double precision, intent(inout), dimension(n) :: b
  double precision, intent(out), dimension(n) :: c  
  b = b * 2
  c = real(b)
end subroutine

subroutine other(n, b)
  integer, intent(in) :: n
  double precision, intent(inout), dimension(n) :: b
end subroutine

subroutine cfoo(n, b, c)
  integer, intent(in) :: n
  complex, intent(inout), dimension(n) :: b
  real, intent(out), dimension(n) :: c
  b = b * 3
  c = real(b)
end subroutine

subroutine zfoo(n, b, c)
  integer, intent(in) :: n
  double complex, intent(inout), dimension(n) :: b
  double precision, intent(out), dimension(n) :: c
  b = b * 4
  c = real(b)
end subroutine

!
! Test both that keyword conflict/name mangling works, and
! single, non-array argument
!

subroutine slass(x, flag)
  implicit none
  real, intent(inout) :: x
  character, intent(in) :: flag
  x = x * 2
end subroutine

subroutine dlass(x, flag)
  implicit none
  double precision, intent(inout) :: x
  character, intent(in) :: flag
  x = x * 2
end subroutine

subroutine class(x, flag)
  implicit none
  complex, intent(inout) :: x
  character, intent(in) :: flag
  x = x * 2
end subroutine

subroutine zlass(x, flag)
  implicit none
  double complex, intent(inout) :: x
  character, intent(in) :: flag
  x = x * 2
end subroutine

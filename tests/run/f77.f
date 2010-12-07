C configure-flags: --f77binding

      subroutine int_default(i1,i2,i3)
      implicit none
      integer, intent(in) :: i1
      integer, intent(inout) :: i2
      integer, intent(out) :: i3
      i3 = i1 + i1
      i2 = i2 + 2*i3
      end subroutine
      subroutine int_x_len(i4,i5,i6,i7,i8,i9,i10,i11,i12,i13,i14,i15)
      implicit none
      integer*1, intent(in) :: i4
      integer*1, intent(inout) :: i5
      integer*1, intent(out) :: i6
      integer*2, intent(in) :: i7
      integer*2, intent(inout) :: i8
      integer*2, intent(out) :: i9
      integer*4, intent(in) :: i10
      integer*4, intent(inout) :: i11
      integer*4, intent(out) :: i12
      integer*8, intent(in) :: i13
      integer*8, intent(inout) :: i14
      integer*8, intent(out) :: i15
      i6 = i4 + i5
      i9 = i7 + i8
      i12 = i10 + i11
      i15 = i13 + i14
      end subroutine
      subroutine int_kind_x(i1,i2,i3,i4,i5,i6,i7,i8,i9,i10,i11,i12)
      implicit none
      integer(kind=1), intent(in) :: i1
      integer(kind=1), intent(inout) :: i2
      integer(kind=1), intent(out) :: i3
      integer(kind=2), intent(in) :: i4
      integer(kind=2), intent(inout) :: i5
      integer(kind=2), intent(out) :: i6
      integer(kind=4), intent(in) :: i7
      integer(kind=4), intent(inout) :: i8
      integer(kind=4), intent(out) :: i9
      integer(kind=8), intent(in) :: i10
      integer(kind=8), intent(inout) :: i11
      integer(kind=8), intent(out) :: i12
      i3 = i1 + i2
      i6 = i4 + i5
      i9 = i7 + i8
      i12 = i10 + i11
      end subroutine

      subroutine explicit_shape(n1, n2, ain, aout, ainout, ano)
        implicit none
        integer, intent(in) :: n1, n2
        real, dimension(n1, n2), intent(in) :: ain
        real, dimension(n1, n2), intent(out) :: aout
        real, dimension(n1, n2), intent(inout) :: ainout
        real, dimension(n1, n2) :: ano

        aout = ain
        ano = ainout
        ainout = ain + ano
      end subroutine explicit_shape

      subroutine assumed_size(n1, n2, ain, aout, ainout, ano)
        implicit none
        integer, intent(in) :: n1, n2
        real, dimension(n1, *), intent(in) :: ain
        real, dimension(n1, *), intent(out) :: aout
        real, dimension(n1, *), intent(inout) :: ainout
        real, dimension(n1, *) :: ano

        aout(:,1:n2) = ain(:,1:n2)
        ano(:,1:n2) = ainout(:,1:n2)
        ainout(:,1:n2) = ain(:,1:n2) + ano(:,1:n2)
      end subroutine assumed_size

      subroutine double_if_A(x, y)
        character, intent(in) :: x
        integer, intent(inout) :: y
        if (x .eq. 'A') then
           y = y * 2
        endif
      end subroutine

      subroutine emit_F(x)
        character, intent(out) :: x
        x = 'F'
      end subroutine

C TODO: Does not work
c$$$      logical function lsame(ca,cb)
c$$$      character ca,cb
c$$$      intrinsic ichar
c$$$      integer inta,intb,zcode
c$$$      lsame = .true.
c$$$      end
